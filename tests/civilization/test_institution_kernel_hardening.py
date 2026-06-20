from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]
CIVI_TABLES = [
    "agent_membership_edges", "institution_contracts",
    "institution_output_reviews", "civilization_memory_events",
    "governance_decisions", "departments", "institutions",
]


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/006_civilization.sql").read_text())
    yield conn
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    conn.close()


def _contract(name: str) -> dict:
    return {
        "institution_name": name,
        "accepted_inputs": ["software_request"],
        "produced_outputs": ["software_artifact"],
        "verification_required": True,
        "required_external_reviewer": f"{name}-External",
        "failure_conditions": ["invalid_output"],
        "escalation_target": "governance",
        "reputation_metric": "overall_log_score",
    }


def _inst(db, name: str | None = None) -> dict:
    from civilization.services.institution_service import create_institution

    name = name or f"Inst-{uuid.uuid4().hex[:8]}"
    return create_institution(name, _contract(name), db)


def test_duplicate_institution_blocked_at_creation_service(db) -> None:
    from civilization.services.institution_service import create_institution

    name = f"Dup-{uuid.uuid4().hex[:6]}"
    create_institution(name, _contract(name), db)

    with pytest.raises(ValueError, match="DUPLICATE INSTITUTION"):
        create_institution(name, _contract(name), db)


def test_institution_creation_budget_enforced(db, tmp_path, monkeypatch) -> None:
    from civilization.services import institution_service

    controls = tmp_path / "controls.yaml"
    controls.write_text(
        "institution_creation_budget: 1\n"
        "duplicate_institution_detector: true\n"
    )
    monkeypatch.setattr(institution_service, "CONTROLS_FILE", controls)

    _inst(db, "BudgetOne")
    with pytest.raises(ValueError, match="INSTITUTION CREATION BUDGET EXCEEDED"):
        _inst(db, "BudgetTwo")


def test_role_validation_membership_expiry_and_eviction(db) -> None:
    from civilization.services.institution_service import (
        add_agent_membership,
        evict_agent,
        list_active_members,
    )

    inst = _inst(db)
    dept_id = inst["department_ids"]["Production"]

    with pytest.raises(ValueError, match="Invalid role_name"):
        add_agent_membership("agent-invalid", dept_id, "self_certifier", db)

    add_agent_membership(
        "agent-expired",
        dept_id,
        "contributor",
        db,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    add_agent_membership("agent-active", dept_id, "reviewer", db)
    assert "agent-expired" not in list_active_members(dept_id, db)
    assert "agent-active" in list_active_members(dept_id, db)

    evict_agent("agent-active", dept_id, "failed review", db)
    assert "agent-active" not in list_active_members(dept_id, db)


def test_challenged_review_resolution_writes_challenge_resolved(db) -> None:
    from civilization.services.review_service import create_review, transition_review

    producer = _inst(db, "Producer")
    reviewer = _inst(db, "Reviewer")
    review_id = create_review("out-challenge", producer["institution_id"], reviewer["institution_id"], db)

    transition_review(review_id, "under_review", db)
    transition_review(review_id, "challenged", db, evidence={"reason": "missing proof"})
    transition_review(review_id, "approved", db, evidence={"resolution": "proof accepted"})

    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events "
            "WHERE event_type = 'challenge_resolved' AND evidence_refs->>'review_id' = %s",
            (review_id,),
        )
        assert cur.fetchone()[0] == 1


def test_review_timeout_escalates_to_failure_memory(db, tmp_path, monkeypatch) -> None:
    from civilization.services import review_service
    from civilization.services.review_service import create_review, escalate_review_timeouts

    controls = tmp_path / "controls.yaml"
    controls.write_text("review_timeout_hours: 1\n")
    monkeypatch.setattr(review_service, "CONTROLS_FILE", controls)

    producer = _inst(db, "TimeoutProducer")
    reviewer = _inst(db, "TimeoutReviewer")
    review_id = create_review("out-timeout", producer["institution_id"], reviewer["institution_id"], db)
    with db.cursor() as cur:
        cur.execute(
            "UPDATE institution_output_reviews SET created_at = %s WHERE id = %s",
            (datetime.now(timezone.utc) - timedelta(hours=2), review_id),
        )

    assert review_id in escalate_review_timeouts(db)
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events "
            "WHERE event_type = 'failure_recorded' AND evidence_refs->>'review_id' = %s",
            (review_id,),
        )
        assert cur.fetchone()[0] == 1


def test_cross_institution_reputation_view_lists_institutions(db) -> None:
    from civilization.services.institution_service import get_cross_institution_reputation

    first = _inst(db, "CrossA")
    second = _inst(db, "CrossB")

    view = get_cross_institution_reputation(db)
    ids = {row["institution_id"] for row in view}
    assert {first["institution_id"], second["institution_id"]}.issubset(ids)
    assert all(row["department_count"] == 5 for row in view)
