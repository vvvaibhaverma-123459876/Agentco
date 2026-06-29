import os
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

ROOT = Path(__file__).resolve().parents[2]


def _dsn():
    dsn = os.environ.get("DATABASE_URL") or os.environ.get("AGENTCO_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL or AGENTCO_TEST_DATABASE_URL required for spend ledger integration")
    return dsn


def _apply_migrations():
    conn = psycopg2.connect(_dsn())
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            for name in (
                "079_identity_authority.sql",
                "080_event_log.sql",
                "081_resource_ledger.sql",
                "082_resource_reservations.sql",
            ):
                cur.execute((ROOT / "backend" / "src" / "db" / "migrations" / name).read_text())
    finally:
        conn.close()


def _account_state(account_id: str):
    conn = psycopg2.connect(_dsn())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT balance, reserved_balance
                  FROM civilization_resource_accounts
                 WHERE id = %s
                """,
                [account_id],
            )
            row = cur.fetchone()
            return float(row[0]), float(row[1])
    finally:
        conn.close()


@pytest.fixture(autouse=True)
def spend_ledger_env(monkeypatch):
    _apply_migrations()
    monkeypatch.setenv("AGENTCO_SPEND_LEDGER_ENABLED", "1")
    monkeypatch.setenv("LLM_LEDGER_RESERVATION_TOKENS", "100")
    monkeypatch.setenv("LLM_LEDGER_RESERVATION_TTL_SECONDS", "60")
    yield


def test_spend_guardrail_reserves_and_settles_real_ledger():
    from runtime.base_agent.spend_guardrail import SpendGuardrail
    from runtime.base_agent.spend_ledger import PostgresSpendLedger

    agent_id = f"spend-ledger-agent-{uuid.uuid4()}"
    ledger = PostgresSpendLedger(dsn=_dsn(), agent_id=agent_id, model_name="test-model", max_tokens=1000)
    ledger.initialize()
    ledger.allocate(100, idempotency_key=f"allocate-{agent_id}", reason="test token budget")

    guardrail = SpendGuardrail(max_tokens=1000, agent_id=agent_id, model_name="test-model", ledger=ledger)
    guardrail.check_before_call()
    assert _account_state(ledger.account_id) == (100.0, 100.0)

    guardrail.record_usage(40)
    assert guardrail.tokens_used == 40
    assert _account_state(ledger.account_id) == (60.0, 0.0)


def test_spend_guardrail_releases_pending_reservation_on_failed_call():
    from runtime.base_agent.spend_guardrail import SpendGuardrail
    from runtime.base_agent.spend_ledger import PostgresSpendLedger

    agent_id = f"spend-ledger-release-agent-{uuid.uuid4()}"
    ledger = PostgresSpendLedger(dsn=_dsn(), agent_id=agent_id, model_name="test-model", max_tokens=1000)
    ledger.initialize()
    ledger.allocate(100, idempotency_key=f"allocate-{agent_id}", reason="test token budget")

    guardrail = SpendGuardrail(max_tokens=1000, agent_id=agent_id, model_name="test-model", ledger=ledger)
    guardrail.check_before_call()
    assert _account_state(ledger.account_id) == (100.0, 100.0)

    guardrail.release_pending_reservation()
    assert _account_state(ledger.account_id) == (100.0, 0.0)


def test_spend_guardrail_blocks_when_real_ledger_budget_is_missing():
    from runtime.base_agent.spend_guardrail import SpendCapExceeded, SpendGuardrail
    from runtime.base_agent.spend_ledger import PostgresSpendLedger

    agent_id = f"spend-ledger-block-agent-{uuid.uuid4()}"
    ledger = PostgresSpendLedger(dsn=_dsn(), agent_id=agent_id, model_name="test-model", max_tokens=1000)
    ledger.initialize()
    guardrail = SpendGuardrail(max_tokens=1000, agent_id=agent_id, model_name="test-model", ledger=ledger)

    with pytest.raises(SpendCapExceeded, match="insufficient available llm_tokens balance"):
        guardrail.check_before_call()


def test_structured_output_releases_ledger_hold_when_provider_call_fails():
    from runtime.base_agent.spend_guardrail import SpendGuardrail
    from runtime.base_agent.spend_ledger import PostgresSpendLedger
    from runtime.base_agent.structured_output import get_validated_output

    agent_id = f"spend-ledger-structured-agent-{uuid.uuid4()}"
    ledger = PostgresSpendLedger(dsn=_dsn(), agent_id=agent_id, model_name="test-model", max_tokens=1000)
    ledger.initialize()
    ledger.allocate(100, idempotency_key=f"allocate-{agent_id}", reason="test token budget")
    guardrail = SpendGuardrail(max_tokens=1000, agent_id=agent_id, model_name="test-model", ledger=ledger)

    class FailingCompletions:
        def create(self, **_kwargs):
            raise RuntimeError("provider unavailable")

    client = SimpleNamespace(chat=SimpleNamespace(completions=FailingCompletions()))
    with pytest.raises(RuntimeError, match="provider unavailable"):
        get_validated_output(client, "test-model", [], {"type": "object"}, SimpleNamespace(route=lambda **_: {}), guardrail=guardrail)

    assert _account_state(ledger.account_id) == (100.0, 0.0)
