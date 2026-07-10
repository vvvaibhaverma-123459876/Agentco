"""
Epistemic Reserve — AgentCo agent integration test.

Proves that an AgentCo BaseAgentV2 agent is a first-class Reserve participant:
  - Agent pre-registers a prediction via pre_register_claim() (hardness computed on INSERT).
  - Resolution service resolves it against external ground truth.
  - Agent calls refresh_reserve_credential() → real credential issued from real ledger rows.
  - Credential is independently verifiable and durably persisted.

Run:
  AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5433/agentco?host=/tmp \\
    python3 -m pytest reserve/tests/test_agent_reserve_integration.py -v -s
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

from calibration import create_calibration_engine
from reserve import create_reserve_engine, verify_credential
from reserve.tests.dsn import reserve_test_dsn

try:
    DSN = reserve_test_dsn(__file__)
except Exception as exc:
    pytest.skip(str(exc), allow_module_level=True)
MIGRATION_ROOT = Path(__file__).resolve().parents[2]


def _apply_migrations(cur):
    ledger_sql = (MIGRATION_ROOT / "backend/src/db/migrations/011_prediction_ledger.sql").read_text()
    reserve_sql = (MIGRATION_ROOT / "reserve/migrations/001_reserve_extension.sql").read_text()
    ed25519_sql = (MIGRATION_ROOT / "reserve/migrations/004_ed25519_signature.sql").read_text()
    for tbl in ("calibration_credentials", "credential_domains", "prediction_ledger"):
        cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    cur.execute(ledger_sql)
    cur.execute(reserve_sql)
    cur.execute(ed25519_sql)
    cur.execute(
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
        "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
    )
    cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
    cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    cur.execute(
        "DO $$ BEGIN GRANT resolution_service TO agentco; "
        "EXCEPTION WHEN insufficient_privilege THEN NULL; END $$;"
    )


@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        _apply_migrations(cur)
    yield conn
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE")
        cur.execute("ALTER TABLE prediction_ledger DISABLE TRIGGER ALL")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE")
    conn.close()


def test_agent_earns_reserve_credential_from_real_predictions(db, monkeypatch):
    """
    Full path: BaseAgentV2 → pre_register_claim → resolve → refresh_reserve_credential.
    Proves hardness is written on INSERT and credential is independently verifiable.
    """
    from runtime.base_agent.base_agent_v2 import BaseAgentV2
    from runtime.base_agent.llm_client import clear_client_cache

    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_API_KEY", "ollama")
    clear_client_cache()

    cal = create_calibration_engine(db=db)

    class _TestAgent(BaseAgentV2):
        PROMPT_VERSION = "1.0.0-reserve-test"
        def run(self, task):
            return None

    agent = _TestAgent(agent_id="reserve-integration-agent", calibration_engine=cal)

    # Register 3 predictions (past resolution_date so they can be resolved immediately)
    past = datetime.now(timezone.utc) - timedelta(days=2)
    pids = []
    for i in range(3):
        pid = agent.pre_register_claim(
            claim=f"Integration test claim {i}: metric will exceed threshold",
            probability=0.72,
            resolution_criterion="metric dashboard reading",
            resolution_date=past,
            domain="engineering",
            claim_type="forecast",
            ground_truth_source="external_monitoring",
            historical_registration_reason="test fixture seeds already-resolved historical predictions",
        )
        assert pid is not None
        pids.append(pid)
    print(f"\n[integration] Registered {len(pids)} predictions via BaseAgentV2")

    # Verify hardness was written on INSERT
    with db.cursor() as cur:
        cur.execute(
            "SELECT prediction_id, hardness FROM prediction_ledger "
            "WHERE producing_agent_id = 'reserve-integration-agent'",
        )
        rows = cur.fetchall()
    assert len(rows) == 3
    expected_hardness = round(2.0 * 0.72 * (1.0 - 0.72), 10)
    for pid, h in rows:
        actual = round(float(h), 10)
        assert abs(actual - expected_hardness) < 1e-6, \
            f"hardness={actual} expected≈{expected_hardness} for p=0.72"
    print(f"[integration] hardness={float(rows[0][1]):.4f} correctly set on INSERT for all 3 rows")

    # Resolve via resolution_service role
    res_conn = psycopg2.connect(DSN)
    res_conn.autocommit = True
    with res_conn.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    res_cal = create_calibration_engine(db=res_conn)
    for pid in pids:
        rec = res_cal["ledger"].get(pid) or cal["ledger"].get(pid)
        if res_cal["ledger"].get(pid) is None:
            res_cal["ledger"]._in_memory[pid] = rec
        res_cal["resolution"].resolve(
            prediction_id=pid,
            outcome=True,
            ground_truth_source="external_monitoring",
            evidence={"source": "integration_test"},
        )
        res_cal["ledger"].persist_resolution(res_cal["ledger"].get(pid))
    res_conn.close()

    # Reload ledger cache to see resolutions
    cal["ledger"]._in_memory.clear()
    cal["ledger"]._load_from_db()
    print(f"[integration] Resolved all {len(pids)} predictions TRUE via resolution_service")

    # Issue Reserve credential via BaseAgentV2
    cred = agent.refresh_reserve_credential()

    assert cred is not None, "refresh_reserve_credential() must return a credential"
    assert cred.agent_id == "reserve-integration-agent"
    assert cred.sample_count == 3
    assert len(cred.cells) == 1  # one (engineering, short) cell
    assert cred.cells[0].domain == "engineering"
    assert verify_credential(cred), "Credential HMAC must verify"

    # Verify credential was persisted to DB
    with db.cursor() as cur:
        cur.execute(
            "SELECT agent_id, sample_count FROM calibration_credentials "
            "WHERE credential_id = %s",
            (cred.credential_id,),
        )
        row = cur.fetchone()
    assert row is not None and row[0] == "reserve-integration-agent" and row[1] == 3

    print(f"[integration] Credential issued: id={cred.credential_id[:8]} "
          f"cells={len(cred.cells)} sample_count={cred.sample_count} "
          f"log={cred.overall_log_score:.4f} verified=True persisted=True")
    print("[integration] PASS: BaseAgentV2 is a first-class Reserve participant")
