"""
Test suite for Society Layer (Phase J).

Tests:
- create society
- admit institution through governance
- duplicate admission rejected
- institution can be suspended from society
- society reputation computed from member institutions
- society cannot judge dispute where society itself is defendant
- society can assign external reviewer from different institution
"""
from __future__ import annotations

import pytest
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

from civilization.societies import (
    create_society,
    get_society,
    list_societies,
    admit_institution,
    suspend_institution_from_society,
    get_society_members,
    assign_external_reviewer,
    propose_admission,
    approve_proposal,
    compute_society_reputation,
    aggregate_member_reputations,
    can_society_judge_dispute,
)
from civilization.services.institution_service import create_institution

TEST_DB_URL = "postgresql://agentco:password@localhost:5433/agentco?host=/tmp"


@pytest.fixture
def db():
    """Fixture for database connection."""
    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture
def clean_db(db):
    """Fixture to clean societies tables before and after test."""
    with db.cursor() as cur:
        try:
            cur.execute("DELETE FROM society_audit_log")
            cur.execute("DELETE FROM society_institution_edges")
            cur.execute("DELETE FROM societies")
            cur.execute("DELETE FROM society_governance_proposals")
            cur.execute("DELETE FROM dispute_rulings")
            cur.execute("DELETE FROM disputes")
        except:
            pass
    yield db


def test_create_society(clean_db):
    """Test creating a new society."""
    society = create_society(
        name="Engineering Society",
        domain="engineering",
        purpose="Govern engineering practices and standards",
        authority_scope=["engineering", "architecture"],
        db=clean_db,
    )

    assert society.name == "Engineering Society"
    assert society.domain == "engineering"
    assert society.status == "active"
    assert society.reputation_score == 0.0

    retrieved = get_society(society.id, clean_db)
    assert retrieved is not None
    assert retrieved.name == "Engineering Society"


def test_admit_institution_through_governance(clean_db):
    """Test admitting an institution through governance proposal + approval."""
    society = create_society(
        name="Safety Society",
        domain="safety",
        purpose="Govern safety standards",
        db=clean_db,
    )

    contract = {
        "institution_name": "Safety Labs",
        "accepted_inputs": ["safety review requests"],
        "produced_outputs": ["safety certifications"],
        "verification_required": True,
        "required_external_reviewer": "Engineering Labs",
        "failure_conditions": ["certification revoked"],
        "escalation_target": "CEO",
        "reputation_metric": "safety_score",
    }
    inst_result = create_institution("Safety Labs", contract, clean_db)
    institution_id = inst_result["institution_id"]

    proposal = propose_admission(society.id, institution_id, "admin", clean_db)
    assert proposal["proposal_type"] == "admission"
    assert proposal["status"] == "open"

    approved = approve_proposal(society.id, proposal["proposal_id"], "admin", clean_db)
    assert approved["status"] == "approved"

    members = get_society_members(society.id, clean_db)
    assert len(members) == 1
    assert members[0]["institution_id"] == institution_id


def test_duplicate_admission_rejected(clean_db):
    """Test that duplicate institution admission is rejected."""
    society = create_society(
        name="Econ Society",
        domain="economics",
        purpose="Govern economic standards",
        db=clean_db,
    )

    contract = {
        "institution_name": "Econ Labs",
        "accepted_inputs": ["economic analysis"],
        "produced_outputs": ["economic reports"],
        "verification_required": True,
        "required_external_reviewer": "Finance Labs",
        "failure_conditions": ["report invalidated"],
        "escalation_target": "CFO",
        "reputation_metric": "econ_score",
    }
    inst_result = create_institution("Econ Labs", contract, clean_db)
    institution_id = inst_result["institution_id"]

    admit_institution(society.id, institution_id, "member", clean_db)

    with pytest.raises(ValueError, match="already active"):
        admit_institution(society.id, institution_id, "member", clean_db)


def test_institution_can_be_suspended(clean_db):
    """Test suspending an institution from a society."""
    society = create_society(
        name="Governance Society",
        domain="governance",
        purpose="Govern governance standards",
        db=clean_db,
    )

    contract = {
        "institution_name": "Governance Labs",
        "accepted_inputs": ["governance requests"],
        "produced_outputs": ["governance decisions"],
        "verification_required": True,
        "required_external_reviewer": "Audit Labs",
        "failure_conditions": ["decision overturned"],
        "escalation_target": "Board",
        "reputation_metric": "governance_score",
    }
    inst_result = create_institution("Governance Labs", contract, clean_db)
    institution_id = inst_result["institution_id"]

    admit_institution(society.id, institution_id, "member", clean_db)
    from civilization.societies import suspend_institution_from_society
    suspend_institution_from_society(society.id, institution_id, clean_db)

    members = get_society_members(society.id, clean_db, active_only=False)
    active_members = get_society_members(society.id, clean_db, active_only=True)

    assert len(members) == 1
    assert members[0]["membership_status"] == "suspended"
    assert len(active_members) == 0


def test_society_reputation_from_members(clean_db):
    """Test that society reputation is aggregated from member institutions."""
    society = create_society(
        name="Memory Society",
        domain="memory",
        purpose="Govern memory standards",
        db=clean_db,
    )

    contract1 = {
        "institution_name": "Memory Lab 1",
        "accepted_inputs": ["memory tests"],
        "produced_outputs": ["memory reports"],
        "verification_required": True,
        "required_external_reviewer": "Memory Lab 2",
        "failure_conditions": ["report rejected"],
        "escalation_target": "CEO",
        "reputation_metric": "memory_score",
    }
    inst1 = create_institution("Memory Lab 1", contract1, clean_db)

    contract2 = {
        "institution_name": "Memory Lab 2",
        "accepted_inputs": ["memory tests"],
        "produced_outputs": ["memory reports"],
        "verification_required": True,
        "required_external_reviewer": "Memory Lab 1",
        "failure_conditions": ["report rejected"],
        "escalation_target": "CEO",
        "reputation_metric": "memory_score",
    }
    inst2 = create_institution("Memory Lab 2", contract2, clean_db)

    with clean_db.cursor() as cur:
        cur.execute("UPDATE institutions SET reputation_score = 0.8 WHERE id = %s", (inst1["institution_id"],))
        cur.execute("UPDATE institutions SET reputation_score = 0.6 WHERE id = %s", (inst2["institution_id"],))

    admit_institution(society.id, inst1["institution_id"], "member", clean_db)
    admit_institution(society.id, inst2["institution_id"], "member", clean_db)

    rep = compute_society_reputation(society.id, clean_db)
    assert abs(rep - 0.7) < 0.01

    agg = aggregate_member_reputations(society.id, clean_db)
    assert agg["member_count"] == 2
    assert abs(agg["average_reputation"] - 0.7) < 0.01


def test_society_cannot_judge_own_dispute(clean_db):
    """Test that a society cannot judge a dispute where it is the defendant."""
    society = create_society(
        name="Justice Society",
        domain="justice",
        purpose="Govern justice standards",
        db=clean_db,
    )

    with clean_db.cursor() as cur:
        dispute_id = "test-dispute-123"
        cur.execute(
            """
            INSERT INTO disputes (id, dispute_type, plaintiff_id, defendant_id, subject, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (dispute_id, "inter_institution", "some-institution", society.id, "alleged wrongdoing", "open"),
        )

    can_judge = can_society_judge_dispute(society.id, dispute_id, clean_db)
    assert not can_judge


def test_assign_external_reviewer(clean_db):
    """Test assigning an external reviewer from a different institution."""
    society = create_society(
        name="Review Society",
        domain="review",
        purpose="Govern review standards",
        db=clean_db,
    )

    contract1 = {
        "institution_name": "Review Lab A",
        "accepted_inputs": ["review requests"],
        "produced_outputs": ["review reports"],
        "verification_required": True,
        "required_external_reviewer": "Review Lab B",
        "failure_conditions": ["review rejected"],
        "escalation_target": "CEO",
        "reputation_metric": "review_score",
    }
    inst1 = create_institution("Review Lab A", contract1, clean_db)

    contract2 = {
        "institution_name": "Review Lab B",
        "accepted_inputs": ["review requests"],
        "produced_outputs": ["review reports"],
        "verification_required": True,
        "required_external_reviewer": "Review Lab A",
        "failure_conditions": ["review rejected"],
        "escalation_target": "CEO",
        "reputation_metric": "review_score",
    }
    inst2 = create_institution("Review Lab B", contract2, clean_db)

    admit_institution(society.id, inst1["institution_id"], "member", clean_db)
    admit_institution(society.id, inst2["institution_id"], "member", clean_db)

    assignment = assign_external_reviewer(
        society.id,
        inst1["institution_id"],
        inst2["institution_id"],
        clean_db,
    )

    assert assignment["reviewer_institution_id"] == inst2["institution_id"]
    assert assignment["institution_id"] == inst1["institution_id"]

    with pytest.raises(ValueError, match="must differ"):
        assign_external_reviewer(
            society.id,
            inst1["institution_id"],
            inst1["institution_id"],
            clean_db,
        )
