"""
Real-Postgres round-trip test for the DB-wired PredictionLedger.

Proves that PredictionLedger(db=conn):
  - durably INSERTs a pre-registration into the prediction_ledger table,
  - hydrates its cache from the DB on construction (_load_from_db),
  - mirrors a resolution back to the DB via persist_resolution() using the
    resolution_service role (the only role the DB trigger permits).

Skipped unless AGENTCO_TEST_DATABASE_URL points at a reachable Postgres.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

from calibration.ledger.prediction_ledger import PredictionLedger, PredictionRegistration

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
if DSN:
    try:
        import sys as _sys
        from pathlib import Path as _Path

        _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
        from pg_test_isolation import isolated_dsn

        # Destructive fixture: run in an isolated sibling database so the
        # shared prediction_ledger is never dropped out from under other suites.
        DSN = isolated_dsn(DSN)
    except Exception:
        DSN = None  # Postgres unreachable; the skip guard below handles it
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set — real Postgres required"
)

MIGRATION_REL = "backend/src/db/migrations/011_prediction_ledger.sql"


@pytest.fixture()
def fresh_table():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    admin = psycopg2.connect(DSN)
    admin.autocommit = True
    sql = (root / MIGRATION_REL).read_text()
    reserve_sql = (root / "reserve" / "migrations" / "001_reserve_extension.sql").read_text()
    ed25519_sql = (root / "reserve" / "migrations" / "004_ed25519_signature.sql").read_text()
    with admin.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE;")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE;")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
        cur.execute(sql)
        # Reserve extension adds hardness + consequence columns (required by _insert_record).
        cur.execute(reserve_sql)
        cur.execute(ed25519_sql)
        cur.execute(
            "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='resolution_service') "
            "THEN CREATE ROLE resolution_service LOGIN PASSWORD 'test'; END IF; END $$;"
        )
        # PG15+ requires explicit schema USAGE for non-owner roles to see the table.
        cur.execute("GRANT USAGE ON SCHEMA public TO resolution_service;")
        cur.execute("GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;")
    yield admin
    with admin.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE;")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE;")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
    admin.close()


def _reg(resolution_date):
    historical = None
    created_at = None
    if resolution_date <= datetime.now(timezone.utc):
        historical = "deterministic pg persistence fixture"
        created_at = resolution_date - timedelta(seconds=1)
    return PredictionRegistration(
        claim="revenue will exceed target",
        probability=0.8,
        confidence_basis={"basis": "trend"},
        producing_agent_id="cfo-agent",
        producing_prompt_version="1.0.0",
        resolution_criterion="Q-end report",
        resolution_date=resolution_date,
        ground_truth_source="external_accounting_system",
        horizon_class="short",
        domain="finance",
        claim_type="forecast",
        historical_registration_reason=historical,
        created_at=created_at,
    )


def test_pre_register_persists_to_db(fresh_table):
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    ledger = PredictionLedger(db=conn)
    pid = ledger.pre_register(_reg(datetime.now(timezone.utc) + timedelta(days=1)))

    # Row really landed in the table.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT producing_agent_id, probability, resolved FROM prediction_ledger WHERE prediction_id = %s",
            (pid,),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "cfo-agent"
    assert float(row[1]) == 0.8
    assert row[2] is False
    conn.close()


def test_cache_hydrates_from_db(fresh_table):
    # Insert with one ledger instance...
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    pid = PredictionLedger(db=conn).pre_register(
        _reg(datetime.now(timezone.utc) + timedelta(days=1))
    )
    conn.close()

    # ...a brand-new instance must load it from the DB on construction.
    conn2 = psycopg2.connect(DSN)
    conn2.autocommit = True
    ledger2 = PredictionLedger(db=conn2)
    rec = ledger2.get(pid)
    assert rec is not None
    assert rec.producing_agent_id == "cfo-agent"
    conn2.close()


def test_persist_resolution_writes_through_as_service_role(fresh_table):
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    pid = PredictionLedger(db=conn).pre_register(
        _reg(datetime.now(timezone.utc) - timedelta(days=1))  # past => resolvable
    )
    conn.close()

    # Resolve as the resolution_service role (the only role the trigger allows).
    svc = psycopg2.connect(DSN)
    svc.autocommit = True
    with svc.cursor() as cur:
        cur.execute("SET ROLE resolution_service;")
    ledger = PredictionLedger(db=svc)
    rec = ledger.get(pid)
    rec.resolved = True
    rec.resolved_outcome = True
    rec.resolved_at = datetime.now(timezone.utc)
    rec.resolved_by_service = "resolution_service"
    rec.brier_score = 0.04
    rec.log_score = -0.22
    ledger.persist_resolution(rec)

    # Confirm the DB row is now resolved.
    check = psycopg2.connect(DSN)
    check.autocommit = True
    with check.cursor() as cur:
        cur.execute(
            "SELECT resolved, resolved_outcome, brier_score FROM prediction_ledger WHERE prediction_id = %s",
            (pid,),
        )
        row = cur.fetchone()
    assert row[0] is True
    assert row[1] is True
    assert float(row[2]) == 0.04
    svc.close()
    check.close()
