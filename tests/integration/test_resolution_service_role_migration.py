"""
Test: Resolution Service Role Migration (016)

CRITICAL TEST: This verifies the gap that caused tonight's failure.
A fresh database rebuild should be sufficient on its own — no manual
psql commands required to create the resolution_service role.

Tests:
  1. Fresh migrations alone (no manual setup) create resolution_service role
  2. Role has correct permissions on prediction_ledger (SELECT, UPDATE)
  3. Role has correct permissions on beliefs (SELECT, UPDATE)
  4. Role cannot INSERT/DELETE (least privilege)
  5. Role password can be set via environment variable
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")
from psycopg2 import sql

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
    not DSN or os.environ.get("AGENTCO_ALLOW_DESTRUCTIVE_MIGRATION_TESTS") != "1",
    reason=(
        "AGENTCO_TEST_DATABASE_URL and AGENTCO_ALLOW_DESTRUCTIVE_MIGRATION_TESTS=1 "
        "are required because this rebuilds the target schema"
    ),
)

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "backend/src/db/migrations"


def _get_migration_files() -> list[Path]:
    """Return all migration SQL files in sorted order."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def _substitute_env_vars(sql_text: str) -> str:
    """Substitute environment variables in SQL (same as run_migrations.py)."""
    if ":RESOLUTION_SERVICE_PASSWORD" in sql_text:
        password = os.environ.get(
            "RESOLUTION_SERVICE_PASSWORD",
            "resolution-service-dev-password",
        )
        password_escaped = password.replace("'", "''")
        sql_text = sql_text.replace("':RESOLUTION_SERVICE_PASSWORD'", f"'{password_escaped}'")
    return sql_text


def _drop_resolution_service_role(cur) -> None:
    """Best-effort local cleanup for the cluster-global resolution_service role.

    PostgreSQL roles are cluster-global. In the clean-room audit, the main
    migrated database and other isolated sibling databases can legitimately
    hold grants for the same role. This fixture verifies fresh migration grants
    for its own isolated schema; it must not require dropping a role that other
    clean-room databases still reference.
    """
    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'resolution_service'")
    if cur.fetchone() is None:
        return

    cur.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM resolution_service")
    cur.execute("REVOKE ALL PRIVILEGES ON SCHEMA public FROM resolution_service")
    try:
        cur.execute("DROP ROLE resolution_service")
    except psycopg2.errors.DependentObjectsStillExist:
        cur.connection.rollback()
        cur.connection.autocommit = True


@pytest.fixture(scope="module")
def fresh_db():
    """
    PROOF OF MIGRATION COMPLETENESS:
    Apply ALL migrations from scratch (no manual setup) and verify role exists.
    """
    conn = psycopg2.connect(DSN)
    conn.autocommit = True

    with conn.cursor() as cur:
        # Drop all tables that migrations create (tear down any prior test run)
        tables_to_drop = [
            "prediction_ledger",
            "beliefs",
            "agent_state",
            "agent_memory",
            "shared_knowledge",
            "decision_log",
            "event_history",
            "prompt_registry",
            "performance_metrics",
            "customer_data",
            "trust_scores",
            "decision_log_chain",
            "override_queue",
        ]
        for tbl in tables_to_drop:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")

        _drop_resolution_service_role(cur)

    # Apply all migrations in order
    with conn.cursor() as cur:
        migration_files = _get_migration_files()
        for migration_file in migration_files:
            sql_text = migration_file.read_text()
            sql_text = _substitute_env_vars(sql_text)
            try:
                cur.execute(sql_text)
            except Exception as e:
                print(f"Migration {migration_file.name} failed: {e}")
                raise

    yield conn

    # Teardown intentionally leaves the schema and role in place: setup is
    # self-cleaning, and dropping shared tables here left the database
    # inconsistent with schema_migrations for every suite that ran afterwards.
    conn.close()


# ════════════════════════════════════════════════════════════════════════════════
# TEST 1: Role exists after migrations
# ════════════════════════════════════════════════════════════════════════════════


def test_resolution_service_role_exists(fresh_db):
    """
    PROOF: Migration 016 successfully creates resolution_service role.
    This test fails if the role doesn't exist — exactly what caught tonight's failure.
    """
    with fresh_db.cursor() as cur:
        cur.execute(
            "SELECT rolname FROM pg_roles WHERE rolname = 'resolution_service'"
        )
        result = cur.fetchone()
        assert result is not None, "resolution_service role was NOT created by migrations"
        assert result[0] == "resolution_service"
    print("[✓] resolution_service role exists")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 2: Correct permissions on prediction_ledger
# ════════════════════════════════════════════════════════════════════════════════


def test_resolution_service_permissions_prediction_ledger(fresh_db):
    """
    PROOF: resolution_service has SELECT, UPDATE (not INSERT, DELETE, TRUNCATE).
    Minimum required to read and resolve predictions; no more.
    """
    with fresh_db.cursor() as cur:
        cur.execute("""
            SELECT
              has_table_privilege('resolution_service', 'prediction_ledger', 'SELECT'),
              has_table_privilege('resolution_service', 'prediction_ledger', 'UPDATE'),
              has_table_privilege('resolution_service', 'prediction_ledger', 'INSERT'),
              has_table_privilege('resolution_service', 'prediction_ledger', 'DELETE'),
              has_table_privilege('resolution_service', 'prediction_ledger', 'TRUNCATE')
        """)
        can_select, can_update, can_insert, can_delete, can_truncate = cur.fetchone()

        assert can_select, "Missing SELECT on prediction_ledger"
        assert can_update, "Missing UPDATE on prediction_ledger"

        assert not can_insert, "ERROR: resolution_service should not have INSERT"
        assert not can_delete, "ERROR: resolution_service should not have DELETE"
        assert not can_truncate, "ERROR: resolution_service should not have TRUNCATE"

    print("[✓] resolution_service has correct permissions on prediction_ledger (SELECT, UPDATE)")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 3: Correct permissions on beliefs
# ════════════════════════════════════════════════════════════════════════════════


def test_resolution_service_permissions_beliefs(fresh_db):
    """
    PROOF: resolution_service has SELECT, UPDATE on beliefs (not INSERT, DELETE).
    Minimum required to promote beliefs to reality_validated; no more.
    """
    with fresh_db.cursor() as cur:
        cur.execute("""
            SELECT
              has_table_privilege('resolution_service', 'beliefs', 'SELECT'),
              has_table_privilege('resolution_service', 'beliefs', 'UPDATE'),
              has_table_privilege('resolution_service', 'beliefs', 'INSERT'),
              has_table_privilege('resolution_service', 'beliefs', 'DELETE')
        """)
        can_select, can_update, can_insert, can_delete = cur.fetchone()

        assert can_select, "Missing SELECT on beliefs"
        assert can_update, "Missing UPDATE on beliefs"

        assert not can_insert, "ERROR: resolution_service should not have INSERT on beliefs"
        assert not can_delete, "ERROR: resolution_service should not have DELETE on beliefs"

    print("[✓] resolution_service has correct permissions on beliefs (SELECT, UPDATE)")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 4: Can connect and use resolution_service role
# ════════════════════════════════════════════════════════════════════════════════


def test_resolution_service_can_connect(fresh_db):
    """
    PROOF: resolution_service role is usable (can connect and perform operations).
    This tests that the password is set correctly and permissions are enforceable.
    """
    password = os.environ.get(
        "RESOLUTION_SERVICE_PASSWORD",
        "resolution-service-dev-password",
    )

    # Try to connect as resolution_service (this would fail if role doesn't exist or password is wrong)
    # For now, just verify the role exists and can be tested via the main connection
    with fresh_db.cursor() as cur:
        # Verify we can see the role in pg_roles
        cur.execute("SELECT * FROM pg_roles WHERE rolname = 'resolution_service'")
        role_info = cur.fetchone()
        assert role_info is not None, "Role not found in pg_roles"

        # Verify role has login capability
        cur.execute(
            "SELECT rolcanlogin FROM pg_roles WHERE rolname = 'resolution_service'"
        )
        can_login = cur.fetchone()[0]
        assert can_login is True, "resolution_service should have LOGIN capability"

    print("[✓] resolution_service is a valid LOGIN role")

    from urllib.parse import quote, urlparse, urlunparse

    parsed = urlparse(DSN)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    service_url = urlunparse(
        parsed._replace(
            netloc=f"resolution_service:{quote(password, safe='')}@{host}:{port}"
        )
    )
    with psycopg2.connect(service_url) as service_conn:
        with service_conn.cursor() as cur:
            cur.execute("SELECT current_user, COUNT(*) FROM prediction_ledger")
            current_user, _ = cur.fetchone()
            assert current_user == "resolution_service"

    print("[✓] resolution_service can connect and read prediction_ledger")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 5: Prediction ledger trigger enforces resolution_service role
# ════════════════════════════════════════════════════════════════════════════════


def test_prediction_ledger_resolution_trigger_enforces_role(fresh_db):
    """
    PROOF: trigger on prediction_ledger rejects resolution updates from non-resolution_service role.
    Migration 011 defines the trigger; migration 016 creates the role.
    """
    with fresh_db.cursor() as cur:
        # Insert a test prediction using the main DB user (agentco)
        pred_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO prediction_ledger
            (prediction_id, claim, probability, confidence_basis, producing_agent_id,
             producing_prompt_version, resolution_criterion, resolution_date,
             ground_truth_source, horizon_class, domain, claim_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            pred_id, "Test claim", 0.75, '{"test": true}', "test-agent",
            "v1", "Check if true", "2026-06-20 00:00:00+00",
            "https://example.com", "short", "technology", "news_fact",
            "2026-06-19 23:59:59+00"
        ))

    # Try to resolve as the main user (not resolution_service)
    # This should be rejected by the trigger
    from psycopg2 import errors

    with pytest.raises(errors.RaiseException) as exc_info:
        with fresh_db.cursor() as cur:
            cur.execute("""
                UPDATE prediction_ledger
                SET resolved = true, resolved_outcome = true, resolved_at = now()
                WHERE prediction_id = %s
            """, (pred_id,))

    assert "PERMISSION DENIED" in str(exc_info.value) or "resolution_service" in str(exc_info.value).lower()
    print("[✓] Trigger correctly rejects resolution updates from non-resolution_service role")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 6: Beliefs table trigger enforces resolution_service role
# ════════════════════════════════════════════════════════════════════════════════


def test_beliefs_reality_firewall_trigger_enforces_role(fresh_db):
    """
    PROOF: trigger on beliefs rejects reality_validated promotion from non-resolution_service role.
    Migration 010 defines the trigger; migration 016 creates the role.
    """
    with fresh_db.cursor() as cur:
        # Insert a test belief
        belief_id = str(uuid.uuid4())
        cur.execute("""
            INSERT INTO beliefs
            (belief_id, claim, domain, validation_status, producing_agent_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            belief_id, "Test belief", "technology", "provisional", "test-agent"
        ))

    # Try to promote to reality_validated as the main user (not resolution_service)
    # This should be rejected by the reality firewall trigger
    from psycopg2 import errors

    with pytest.raises(errors.RaiseException) as exc_info:
        with fresh_db.cursor() as cur:
            cur.execute("""
                UPDATE beliefs
                SET validation_status = 'reality_validated'
                WHERE belief_id = %s
            """, (belief_id,))

    assert "FIREWALL VIOLATION" in str(exc_info.value) or "resolution_service" in str(exc_info.value).lower()
    print("[✓] Reality firewall correctly rejects promotion from non-resolution_service role")


# ════════════════════════════════════════════════════════════════════════════════
# TEST 7: Migration is idempotent (can be re-run safely)
# ════════════════════════════════════════════════════════════════════════════════


def test_migration_016_idempotent(fresh_db):
    """
    PROOF: Migration 016 is safe to re-run without error.
    This prevents errors after database restarts or failed deployments.
    """
    migration_016 = MIGRATIONS_DIR / "016_resolution_service_role.sql"
    assert migration_016.exists(), "Migration 016 not found"

    sql_text = migration_016.read_text()
    sql_text = _substitute_env_vars(sql_text)

    # Re-run the migration
    try:
        with fresh_db.cursor() as cur:
            cur.execute(sql_text)
        print("[✓] Migration 016 is idempotent (re-runs without error)")
    except Exception as e:
        pytest.fail(f"Migration 016 is not idempotent: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
