from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DSN, reason="AGENTCO_TEST_DATABASE_URL not set - real Postgres required"
)

ROOT = Path(__file__).resolve().parents[2]


def _sql(path: str) -> str:
    return (ROOT / path).read_text()


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for table in (
            "agent_membership_edges",
            "institution_output_reviews",
            "civilization_memory_events",
            "governance_decisions",
            "departments",
            "institutions",
        ):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        cur.execute(_sql("reserve/migrations/006_civilization.sql"))
        cur.execute(_sql("reserve/migrations/018_institution_kernel_hardening.sql"))
    yield conn
    with conn.cursor() as cur:
        for table in (
            "agent_membership_edges",
            "institution_output_reviews",
            "civilization_memory_events",
            "governance_decisions",
            "departments",
            "institutions",
        ):
            cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    conn.close()


def _id() -> str:
    return str(uuid.uuid4())


def _seed_institution_and_department(db) -> tuple[str, str]:
    inst_id = _id()
    dept_id = _id()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO institutions (id, name, purpose, authority_scope) VALUES (%s, 'Inst', 'test', '[]'::jsonb)",
            (inst_id,),
        )
        cur.execute(
            "INSERT INTO departments (id, name, parent_id, purpose, authority_scope) VALUES (%s, 'Dept', %s, 'test', '[]'::jsonb)",
            (dept_id, inst_id),
        )
    return inst_id, dept_id


def test_membership_expiry_and_eviction_write_memory_events(db):
    from civilization.services.membership_service import (
        add_agent_to_department,
        evict_agent,
        expire_memberships,
        list_active_memberships,
    )

    _, dept_id = _seed_institution_and_department(db)
    add_agent_to_department(
        "agent-expiring",
        dept_id,
        "engineer",
        db,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    assert expire_memberships(db) == [("agent-expiring", dept_id)]
    assert list_active_memberships(dept_id, db) == []

    add_agent_to_department("agent-evict", dept_id, "engineer", db)
    evict_agent("agent-evict", dept_id, "policy violation", "reviewer-1", db)
    assert list_active_memberships(dept_id, db) == []

    with db.cursor() as cur:
        cur.execute(
            "SELECT event_type FROM civilization_memory_events WHERE entity_id = %s ORDER BY created_at",
            (dept_id,),
        )
        event_types = [row[0] for row in cur.fetchall()]
    assert "membership_added" in event_types
    assert "membership_expired" in event_types
    assert "membership_evicted" in event_types


def test_review_timeout_escalates_without_auto_approval(db):
    from civilization.services.review_timeout_service import escalate_review_timeouts

    producer_id, _ = _seed_institution_and_department(db)
    reviewer_id, _ = _seed_institution_and_department(db)
    review_id = _id()
    old = datetime.now(timezone.utc) - timedelta(hours=72)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO institution_output_reviews
                (id, output_id, producing_institution_id, reviewer_institution_id, status, created_at, updated_at)
            VALUES (%s, 'output-1', %s, %s, 'under_review', %s, %s)
            """,
            (review_id, producer_id, reviewer_id, old, old),
        )

    assert escalate_review_timeouts(db)
    with db.cursor() as cur:
        cur.execute("SELECT status FROM institution_output_reviews WHERE id = %s", (review_id,))
        assert cur.fetchone()[0] == "under_review"
        cur.execute("SELECT event_type FROM civilization_memory_events WHERE entity_id = %s", (producer_id,))
        assert "review_timed_out" in [row[0] for row in cur.fetchall()]


def test_reputation_floor_suspends_without_manual_reputation_write(db):
    from civilization.services.reputation_floor_service import enforce_reputation_floor

    inst_id, _ = _seed_institution_and_department(db)
    with db.cursor() as cur:
        cur.execute("SET civilization.reputation_update_authorized = 'true'")
        cur.execute("UPDATE institutions SET reputation_score = -3.0 WHERE id = %s", (inst_id,))
        cur.execute("SET civilization.reputation_update_authorized = 'false'")

    suspended = enforce_reputation_floor(db)
    assert suspended[0]["entity_id"] == inst_id
    with db.cursor() as cur:
        cur.execute("SELECT status FROM institutions WHERE id = %s", (inst_id,))
        assert cur.fetchone()[0] == "suspended"
        cur.execute("SELECT event_type FROM civilization_memory_events WHERE entity_id = %s", (inst_id,))
        assert "entity_suspended" in [row[0] for row in cur.fetchall()]
