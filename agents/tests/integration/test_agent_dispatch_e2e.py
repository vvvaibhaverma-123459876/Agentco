"""
Component 7 — End-to-end agent task dispatch against REAL infrastructure.

This test drives a single agent task through the full real path and asserts every
durable side-effect against the REAL backing store (no mocks):

  REAL Postgres prediction_ledger  ← agent pre-registers a falsifiable claim
  REAL Postgres decision_log       ← agent writes a hash-chained audit entry
  REAL Kafka  + event_history      ← agent publishes a signed event, consumed back

LLM leg:
  The agent makes a REAL provider call via its OpenAI-compatible client when an
  endpoint is reachable at LLM_BASE_URL (e.g. a local Ollama serving a real model).
  When no model endpoint is reachable (restricted sandbox egress), ONLY the LLM
  sub-assertion is skipped — the audit/ledger/Kafka legs are still exercised and
  asserted against real infra. This is gated, never mocked.

Run:
  DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \
  KAFKA_BROKERS=localhost:9092 \
    python3 -m pytest agents/tests/integration/test_agent_dispatch_e2e.py -v -s
"""
import asyncio
import json
import os
import socket
import uuid
from datetime import datetime, timedelta, timezone

import psycopg2
import pytest
from kafka import KafkaConsumer

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"
)
BROKERS = os.environ.get("KAFKA_BROKERS", "localhost:9092")

E2E_AGENT = "research-agent"  # has audit_log + event_bus permissions


def _conn():
    c = psycopg2.connect(DB_URL)
    c.autocommit = True
    return c


def _postgres_ready() -> tuple[bool, str]:
    try:
        c = _conn()
        with c.cursor() as cur:
            cur.execute("SELECT to_regclass('public.decision_log'), to_regclass('public.event_history')")
            decision_log, event_history = cur.fetchone()
        c.close()
        if not decision_log or not event_history:
            return False, "live-service: required Postgres tables decision_log/event_history unavailable"
        return True, "live-service: Postgres ready"
    except Exception as exc:
        return False, f"live-service: Postgres unavailable at DATABASE_URL={DB_URL!r}: {exc}"


def _kafka_ready() -> tuple[bool, str]:
    for broker in BROKERS.split(","):
        host, _, port_text = broker.partition(":")
        try:
            with socket.create_connection((host, int(port_text or "9092")), timeout=1.0):
                return True, "live-service: Kafka socket ready"
        except Exception:
            continue
    return False, f"live-service: Kafka unavailable at KAFKA_BROKERS={BROKERS!r}"


_POSTGRES_READY, _POSTGRES_REASON = _postgres_ready()
_KAFKA_READY, _KAFKA_REASON = _kafka_ready()


def _llm_reachable() -> bool:
    """Try a real, tiny chat completion. True only if a real model actually answers."""
    try:
        from runtime.base_agent.llm_client import make_client
        from runtime.base_agent.model_tiers import model_for
        client = make_client()
        resp = client.chat.completions.create(
            model=model_for(E2E_AGENT),
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=8,
        )
        return bool(resp.choices and resp.choices[0].message.content)
    except Exception:
        return False


def _ensure_prediction_ledger(c):
    """Other real-PG tests DROP prediction_ledger in teardown; recreate it if absent
    so this e2e is order-independent within the master-gate run."""
    from pathlib import Path
    with c.cursor() as cur:
        cur.execute("SELECT to_regclass('public.prediction_ledger')")
        root = Path(__file__).resolve().parents[3]
        if cur.fetchone()[0] is None:
            migration = root / "backend" / "src" / "db" / "migrations" / "011_prediction_ledger.sql"
            cur.execute(migration.read_text())
            # Reserve extension adds hardness + consequence columns (required by _insert_record).
            reserve_ext = root / "reserve" / "migrations" / "001_reserve_extension.sql"
            cur.execute(reserve_ext.read_text())
            cur.execute((root / "reserve" / "migrations" / "004_ed25519_signature.sql").read_text())
        else:
            # Table exists but may be missing the reserve extension entirely
            # (calibration_credentials) or just the hardness column.
            reserve_ext = root / "reserve" / "migrations" / "001_reserve_extension.sql"
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='prediction_ledger' AND column_name='hardness'"
            )
            if cur.fetchone() is None:
                cur.execute(reserve_ext.read_text())
            else:
                cur.execute("SELECT to_regclass('public.calibration_credentials')")
                if cur.fetchone()[0] is None:
                    # Ledger columns are already extended; re-running the full
                    # extension would UPDATE ledger rows and trip the
                    # immutability trigger, so apply only the credential DDL.
                    sql_text = reserve_ext.read_text()
                    credentials_ddl = sql_text[sql_text.index("CREATE TABLE IF NOT EXISTS credential_domains") :]
                    cur.execute(credentials_ddl)
            # Apply migration 004 if ed25519_signature column is missing.
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='calibration_credentials' AND column_name='ed25519_signature'"
            )
            if cur.fetchone() is None:
                cur.execute((root / "reserve" / "migrations" / "004_ed25519_signature.sql").read_text())


@pytest.fixture(scope="module")
def db():
    c = _conn()
    _ensure_prediction_ledger(c)
    yield c
    # Cleanup: remove this test's rows (triggers disabled where append-only).
    with c.cursor() as cur:
        cur.execute(
            """DO $$ BEGIN
                 IF EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                            WHERE c.relname = 'decision_log' AND t.tgname = 'trg_decision_log_no_delete') THEN
                   ALTER TABLE decision_log DISABLE TRIGGER trg_decision_log_no_delete;
                 END IF;
               END $$;"""
        )
        cur.execute("DELETE FROM decision_log WHERE agent_id=%s AND input_summary LIKE 'E2E%%'", (E2E_AGENT,))
        cur.execute(
            """DO $$ BEGIN
                 IF EXISTS (SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
                            WHERE c.relname = 'decision_log' AND t.tgname = 'trg_decision_log_no_delete') THEN
                   ALTER TABLE decision_log ENABLE TRIGGER trg_decision_log_no_delete;
                 END IF;
               END $$;"""
        )
        cur.execute(
            """DELETE FROM contradictions
               WHERE prediction_id IN (
                   SELECT prediction_id
                   FROM prediction_ledger
                   WHERE producing_agent_id=%s
               )""",
            ("e2e-dispatch-agent",),
        )
        cur.execute("DELETE FROM prediction_ledger WHERE producing_agent_id=%s", ("e2e-dispatch-agent",))
        cur.execute("DELETE FROM event_history WHERE producer_agent_id=%s", (E2E_AGENT,))
    c.close()


@pytest.mark.skipif(not _POSTGRES_READY, reason=_POSTGRES_REASON)
@pytest.mark.skipif(not _KAFKA_READY, reason=_KAFKA_REASON)
def test_full_dispatch_path_touches_real_postgres_ledger_audit_and_kafka(db):
    """One agent task → real ledger row + real audit row + real Kafka event."""
    from core.tools import register_all_tools
    from core.tools.handlers import handle_audit_log, handle_event_bus
    from core.tool_registry import execute_tool
    from calibration import create_calibration_engine
    from runtime.base_agent.base_agent_v2 import BaseAgentV2

    register_all_tools()

    # 1) Real DB-backed calibration engine (real prediction_ledger)
    cal = create_calibration_engine(db=db)

    class _DispatchAgent(BaseAgentV2):
        PROMPT_VERSION = "1.0.0-e2e"
        def run(self, task):  # not used directly here
            return None

    agent = _DispatchAgent(agent_id="e2e-dispatch-agent", calibration_engine=cal)

    marker = f"E2E-{uuid.uuid4().hex[:8]}"
    correlation_id = str(uuid.uuid4())

    # 2) LLM leg — REAL provider call when reachable, otherwise skip ONLY this leg.
    llm_ok = _llm_reachable()
    if llm_ok:
        out = agent.act(
            messages=[{"role": "user", "content": f"In one word, classify task {marker} as: routine"}],
        )
        assert out is not None  # real model produced structured output
        print(f"[e2e] REAL LLM call succeeded: {out!r}")
    else:
        print("[e2e] LLM endpoint unreachable in this sandbox — skipping ONLY the live-inference "
              "sub-assertion; audit/ledger/Kafka legs still exercised against real infra.")

    # 3) Real prediction registered in real Postgres prediction_ledger
    pid = agent.pre_register_claim(
        claim=f"{marker}: dispatched task will complete within SLA",
        probability=0.72,
        resolution_criterion="task marked done in tracker",
        resolution_date=datetime.now(timezone.utc) + timedelta(days=3),
        domain="engineering",
        claim_type="forecast",
        ground_truth_source="external_auditor",
    )
    assert pid is not None
    with db.cursor() as cur:
        cur.execute("SELECT producing_agent_id, claim FROM prediction_ledger WHERE prediction_id=%s", (pid,))
        row = cur.fetchone()
    assert row is not None, "prediction must be durably in real Postgres prediction_ledger"
    assert row[0] == "e2e-dispatch-agent"
    assert marker in row[1]

    # 4) Real audit entry written to real Postgres decision_log (via the real tool path,
    #    enforcing real permission check for research-agent → audit_log)
    audit_res = asyncio.run(execute_tool(E2E_AGENT, "audit_log", {
        "agent_id": E2E_AGENT,
        "action_type": "decision",
        "input_summary": f"{marker} dispatch",
        "output_summary": f"prediction_id={pid}",
        "confidence_score": 0.72,
        "risk_level": "low",
        "session_id": correlation_id,
    }))
    log_id = audit_res["log_id"]
    with db.cursor() as cur:
        cur.execute("SELECT chain_hash, prev_hash FROM decision_log WHERE log_id=%s", (log_id,))
        arow = cur.fetchone()
    assert arow is not None, "audit entry must be durably in real Postgres decision_log"
    assert arow[0] and len(arow[0]) == 64, "real hash-chain chain_hash must be present"

    # 5) Real Kafka publish (via real tool path; also INSERTs into event_history)
    event_id = str(uuid.uuid4())
    pub = asyncio.run(execute_tool(E2E_AGENT, "event_bus", {
        "event_id": event_id,
        "event_type": "engineering.task_dispatched",
        "producer_agent_id": E2E_AGENT,
        "payload": {"marker": marker, "prediction_id": pid, "audit_log_id": log_id},
        "confidence_score": 0.72,
        "risk_level": "low",
        "requires_ack": False,
        "correlation_id": correlation_id,
    }))
    assert pub["event_id"] == event_id

    # 5a) Event durably in real event_history
    with db.cursor() as cur:
        cur.execute("SELECT event_type FROM event_history WHERE event_id=%s", (event_id,))
        erow = cur.fetchone()
    assert erow is not None and erow[0] == "engineering.task_dispatched"

    # 5b) Consume the event back OFF the real Kafka topic
    # handle_event_bus maps the "engineering" domain to the agentco.events topic
    consumer = KafkaConsumer(
        "agentco.events",
        bootstrap_servers=BROKERS.split(","),
        auto_offset_reset="earliest",
        consumer_timeout_ms=10000,
        value_deserializer=lambda v: json.loads(v.decode()),
    )
    consumed = False
    for msg in consumer:
        if msg.value.get("event_id") == event_id:
            assert msg.value["producer_agent_id"] == E2E_AGENT
            assert "signature" in msg.value, "event consumed off Kafka must carry HMAC signature"
            consumed = True
            break
    consumer.close()
    assert consumed, "the published event must be consumable from the real Kafka topic"

    print(f"[e2e] PROVEN against real infra — ledger={pid} audit={log_id} "
          f"kafka_event={event_id} (llm_live={llm_ok})")
