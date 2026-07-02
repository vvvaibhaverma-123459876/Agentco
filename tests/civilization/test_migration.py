"""
T3.1 – T3.4 — Civilization migration tests (real Postgres, no mocks).

T3.1  Migration 006 applies cleanly to a fresh DB.
T3.2  Inserting a department with NULL parent_id is REJECTED by the DB.
T3.3  Inserting an institution_output_reviews row with reviewer=producer is REJECTED.
T3.4  A direct UPDATE of reputation_score with no memory-event row is REJECTED by the trigger.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
if DSN:
    try:
        from pg_test_isolation import isolated_dsn

        # Destructive fixture: run in an isolated sibling database so shared
        # backend-migrated tables are never replaced with this suite's schema.
        DSN = isolated_dsn(DSN)
    except Exception:
        DSN = None  # Postgres unreachable; the skip guard below handles it
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set — real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_006 = ROOT / "reserve" / "migrations" / "006_civilization.sql"

CIVI_TABLES = [
    "agent_membership_edges", "institution_contracts",
    "institution_output_reviews", "civilization_memory_events",
    "governance_decisions", "departments", "institutions",
]


def _apply_all(cur):
    cur.execute((ROOT / "backend/src/db/migrations/011_prediction_ledger.sql").read_text())
    cur.execute((ROOT / "reserve/migrations/001_reserve_extension.sql").read_text())
    cur.execute((ROOT / "reserve/migrations/004_ed25519_signature.sql").read_text())
    cur.execute((ROOT / "reserve/migrations/005_prediction_chain.sql").read_text())
    cur.execute(MIGRATION_006.read_text())


@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES + ["prediction_chain_log", "calibration_credentials",
                                   "credential_domains", "prediction_ledger"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        _apply_all(cur)
    yield conn
    # Teardown intentionally leaves the schema in place: each fixture's setup
    # is self-cleaning, and dropping shared tables here left the database
    # inconsistent with schema_migrations for every suite that ran afterwards.
    conn.close()


def _iid():
    return str(uuid.uuid4())


def _insert_institution(cur, iid=None, name="TestInst"):
    iid = iid or _iid()
    cur.execute(
        "INSERT INTO institutions (id, name, purpose, authority_scope) "
        "VALUES (%s, %s, 'test', '[]'::jsonb) RETURNING id",
        (iid, name),
    )
    return iid


# ─── T3.1 ────────────────────────────────────────────────────────────────────

def test_t3_1_migration_applies_cleanly(db):
    """All civilization tables exist after migration 006."""
    with db.cursor() as cur:
        for tbl in CIVI_TABLES:
            cur.execute(
                "SELECT to_regclass(%s)", (f"public.{tbl}",)
            )
            result = cur.fetchone()[0]
            assert result is not None, f"Table {tbl} missing after migration"
    print("\n[T3.1] all civilization tables present ✓")


# ─── T3.2 ────────────────────────────────────────────────────────────────────

def test_t3_2_department_null_parent_rejected(db):
    """Inserting a department with NULL parent_id must be rejected by the DB."""
    with pytest.raises(psycopg2.errors.NotNullViolation):
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO departments (id, name, purpose, authority_scope, parent_id) "
                "VALUES (%s, 'BadDept', 'test', '[]'::jsonb, NULL)",
                (_iid(),),
            )
    print("[T3.2] NULL parent_id on department correctly rejected ✓")


# ─── T3.3 ────────────────────────────────────────────────────────────────────

def test_t3_3_self_certification_ban_enforced(db):
    """reviewer_institution_id = producing_institution_id must be rejected by CHECK constraint."""
    with db.cursor() as cur:
        iid = _insert_institution(cur, name="SelfCertInst")
    with pytest.raises(psycopg2.errors.CheckViolation):
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO institution_output_reviews "
                "(id, output_id, producing_institution_id, reviewer_institution_id) "
                "VALUES (%s, 'out-1', %s, %s)",
                (_iid(), iid, iid),
            )
    print("[T3.3] self-certification ban (reviewer=producer) correctly rejected ✓")


# ─── T3.4 ────────────────────────────────────────────────────────────────────

def test_t3_4_direct_reputation_update_rejected(db):
    """A bare UPDATE of reputation_score without the session flag must raise."""
    with db.cursor() as cur:
        iid = _insert_institution(cur, name="ReputationGuardInst")
    with pytest.raises(psycopg2.errors.RaiseException) as exc:
        with db.cursor() as cur:
            cur.execute(
                "UPDATE institutions SET reputation_score = 0.99 WHERE id = %s", (iid,)
            )
    assert "REPUTATION GUARD" in str(exc.value)
    print("[T3.4] unauthorized reputation_score UPDATE correctly rejected ✓")
