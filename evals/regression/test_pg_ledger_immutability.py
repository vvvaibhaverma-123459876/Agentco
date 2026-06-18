"""
Real-Postgres integration test for the prediction-ledger immutability invariant.

This is the test the spec demands: it issues raw UPDATE / DELETE against the
`prediction_ledger` TABLE (no mocks, no in-memory stand-in) and asserts the
DATABASE itself rejects them. It exercises every layer of
backend/src/db/migrations/011_prediction_ledger.sql:

  1. Pre-registration columns are immutable after INSERT (trigger fires for ALL roles).
  2. DELETE is rejected for non-owner roles (REVOKE DELETE FROM PUBLIC).
  3. Only the `resolution_service` role may write resolution columns (trigger role gate).
  4. Resolution is write-once (cannot re-resolve).
  5. Resolution cannot happen before resolution_date (time gate).
  6. The legitimate path — resolution_service resolving after the date — succeeds.

Skipped automatically unless AGENTCO_TEST_DATABASE_URL points at a reachable
Postgres superuser connection, e.g.:

    AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco

On Windows with the docker-compose stack up, that URL is the default.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set — real Postgres required"
)

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "backend" / "src" / "db" / "migrations" / "011_prediction_ledger.sql"
)


def _admin_conn():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    return conn


@pytest.fixture(scope="module")
def pg():
    """Apply the migration and create the app / resolution_service roles."""
    admin = _admin_conn()
    reserve_ext = (
        Path(__file__).resolve().parents[2]
        / "reserve" / "migrations" / "001_reserve_extension.sql"
    )
    ed25519_ext = (
        Path(__file__).resolve().parents[2]
        / "reserve" / "migrations" / "004_ed25519_signature.sql"
    )
    with admin.cursor() as cur:
        # Clean slate so the suite is repeatable.
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE;")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE;")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
        cur.execute(MIGRATION.read_text())
        # Reserve extension adds hardness + consequence columns (required by _insert_record).
        cur.execute(reserve_ext.read_text())
        cur.execute(ed25519_ext.read_text())

        # An ordinary application writer: gets only PUBLIC privileges, so the
        # REVOKE DELETE/UPDATE FROM PUBLIC actually bites (the table owner would
        # bypass it). Granted INSERT/SELECT so it can pre-register.
        for role in ("ledger_app_writer", "resolution_service"):
            cur.execute(
                "DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{role}') THEN "
                f"CREATE ROLE {role} LOGIN PASSWORD 'test'; END IF; END $$;"
            )
        # PG15+ no longer grants schema-level privileges to non-owner roles by
        # default, so a bare GRANT on the table is not enough — the role also needs
        # USAGE on the schema to resolve the relation name at all.
        for role in ("ledger_app_writer", "resolution_service"):
            cur.execute(f"GRANT USAGE ON SCHEMA public TO {role};")
        cur.execute("GRANT INSERT, SELECT ON prediction_ledger TO ledger_app_writer;")
        # resolution_service is the only role allowed to write resolution columns.
        cur.execute(
            "GRANT INSERT, SELECT, UPDATE ON prediction_ledger TO resolution_service;"
        )
    yield admin
    with admin.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS calibration_credentials CASCADE;")
        cur.execute("DROP TABLE IF EXISTS credential_domains CASCADE;")
        cur.execute("DROP TABLE IF EXISTS prediction_ledger CASCADE;")
    admin.close()


def _role_conn(role: str):
    """Open a connection as a specific role via SET ROLE (keeps one DSN)."""
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(f"SET ROLE {role};")
    return conn


def _insert_prediction(conn, *, resolution_date, resolved=False) -> str:
    pid = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO prediction_ledger
                (prediction_id, claim, probability, producing_agent_id,
                 producing_prompt_version, resolution_criterion, resolution_date,
                 ground_truth_source, horizon_class, domain, claim_type, resolved)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                pid, "test claim", 0.7, "test-agent", "1.0.0",
                "criterion", resolution_date, "external_api", "short",
                "testing", "general", resolved,
            ),
        )
    return pid


def test_pre_registration_columns_are_immutable(pg):
    """A raw UPDATE of a pre-registration column must be rejected by the DB trigger."""
    writer = _role_conn("ledger_app_writer")
    # Insert as the owner/admin so we isolate the UPDATE (writer can insert too,
    # but we want to prove the trigger blocks the edit regardless of role).
    pid = _insert_prediction(pg, resolution_date=datetime.now(timezone.utc) + timedelta(days=1))

    # Even the table owner is subject to the BEFORE UPDATE trigger.
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with pg.cursor() as cur:
            cur.execute(
                "UPDATE prediction_ledger SET claim = 'tampered' WHERE prediction_id = %s;",
                (pid,),
            )
    assert "IMMUTABILITY VIOLATION" in str(exc.value)
    writer.close()


def test_delete_is_rejected_for_non_owner(pg):
    """REVOKE DELETE FROM PUBLIC: a non-owner role cannot delete from the ledger."""
    pid = _insert_prediction(pg, resolution_date=datetime.now(timezone.utc) + timedelta(days=1))
    writer = _role_conn("ledger_app_writer")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        with writer.cursor() as cur:
            cur.execute("DELETE FROM prediction_ledger WHERE prediction_id = %s;", (pid,))
    writer.close()
    # Row is still there.
    with pg.cursor() as cur:
        cur.execute("SELECT count(*) FROM prediction_ledger WHERE prediction_id = %s;", (pid,))
        assert cur.fetchone()[0] == 1


def test_resolution_requires_resolution_service_role(pg):
    """Only resolution_service may write resolution columns (trigger role gate)."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    pid = _insert_prediction(pg, resolution_date=past)
    svc = _role_conn("resolution_service")
    # A role that HAS update privilege would still be blocked by the trigger
    # unless it is resolution_service. We prove the positive case here; the
    # negative role case is covered by the owner attempt below.
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with pg.cursor() as cur:  # admin/owner is NOT resolution_service
            cur.execute(
                "UPDATE prediction_ledger SET resolved = true, resolved_outcome = true, "
                "resolved_at = now(), resolved_by_service = 'x' WHERE prediction_id = %s;",
                (pid,),
            )
    assert "only resolution_service" in str(exc.value)
    svc.close()


def test_legitimate_resolution_succeeds_then_is_write_once(pg):
    """resolution_service can resolve once after the date; a second write is rejected."""
    past = datetime.now(timezone.utc) - timedelta(days=1)
    pid = _insert_prediction(pg, resolution_date=past)
    svc = _role_conn("resolution_service")
    with svc.cursor() as cur:
        cur.execute(
            "UPDATE prediction_ledger SET resolved = true, resolved_outcome = true, "
            "resolved_at = now(), resolved_by_service = 'resolution_service' "
            "WHERE prediction_id = %s;",
            (pid,),
        )
    # Second resolution must be rejected (write-once).
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with svc.cursor() as cur:
            cur.execute(
                "UPDATE prediction_ledger SET resolved_outcome = false WHERE prediction_id = %s;",
                (pid,),
            )
    assert "WRITE-ONCE" in str(exc.value)
    svc.close()


def test_resolution_blocked_before_resolution_date(pg):
    """Time gate: resolution_service cannot resolve before resolution_date."""
    future = datetime.now(timezone.utc) + timedelta(days=7)
    pid = _insert_prediction(pg, resolution_date=future)
    svc = _role_conn("resolution_service")
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with svc.cursor() as cur:
            cur.execute(
                "UPDATE prediction_ledger SET resolved = true, resolved_outcome = true, "
                "resolved_at = now(), resolved_by_service = 'resolution_service' "
                "WHERE prediction_id = %s;",
                (pid,),
            )
    assert "TIME GATE" in str(exc.value)
    svc.close()
