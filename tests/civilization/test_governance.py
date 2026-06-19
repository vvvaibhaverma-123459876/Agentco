"""
Phase 6 — Governance + anti-chaos control tests. Real Postgres, no mocks.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="AGENTCO_TEST_DATABASE_URL not set")

ROOT = Path(__file__).resolve().parents[2]
CIVI_TABLES = [
    "agent_membership_edges", "institution_contracts",
    "institution_output_reviews", "civilization_memory_events",
    "governance_decisions", "departments", "institutions",
]


@pytest.fixture(scope="module")
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES + ["prediction_chain_log", "calibration_credentials",
                                   "credential_domains", "prediction_ledger",
                                   "decision_log"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        for mig in [
            "backend/src/db/migrations/004_decision_log.sql",
            "backend/src/db/migrations/012_decision_log_chain.sql",
            "backend/src/db/migrations/011_prediction_ledger.sql",
            "reserve/migrations/001_reserve_extension.sql",
            "reserve/migrations/004_ed25519_signature.sql",
            "reserve/migrations/005_prediction_chain.sql",
            "reserve/migrations/006_civilization.sql",
        ]:
            cur.execute((ROOT / mig).read_text())
    yield conn
    with conn.cursor() as cur:
        for tbl in CIVI_TABLES + ["prediction_chain_log", "calibration_credentials",
                                   "credential_domains", "prediction_ledger",
                                   "decision_log"]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    conn.close()


def _inst(db, name="TestGovInst"):
    from civilization.services.institution_service import create_institution
    return create_institution(name, {
        "institution_name": name,
        "accepted_inputs": ["a"], "produced_outputs": ["b"],
        "verification_required": True,
        "required_external_reviewer": "Other",
        "failure_conditions": ["f"],
        "escalation_target": "governance",
        "reputation_metric": "overall_log_score",
    }, db)


def test_duplicate_institution_blocked(db):
    """duplicate_institution_detector blocks creating an institution with same name+purpose."""
    from civilization.services.governance_service import propose_decision, GovernanceError
    _inst(db, "DupInst")
    with pytest.raises(GovernanceError, match="DUPLICATE INSTITUTION"):
        propose_decision(
            decision_type="create_institution",
            proposer_entity_id="some-entity",
            payload={"name": "DupInst", "purpose": ""},
            db=db,
        )
    print("\n[gov] duplicate institution blocked ✓")


def test_unresolved_challenge_blocks_high_risk_approval(db):
    """approve_high_risk_output is blocked if there's an open 'challenged' review."""
    from civilization.services.institution_service import create_institution
    from civilization.services.review_service import create_review, transition_review
    from civilization.services.governance_service import propose_decision, approve_decision, GovernanceError

    inst_a = _inst(db, f"GovInstA-{uuid.uuid4().hex[:4]}")
    inst_b = _inst(db, f"GovInstB-{uuid.uuid4().hex[:4]}")
    a_id, b_id = inst_a["institution_id"], inst_b["institution_id"]

    output_id = f"gov-out-{uuid.uuid4().hex[:6]}"
    review_id = create_review(output_id, a_id, b_id, db)
    transition_review(review_id, "under_review", db)
    transition_review(review_id, "challenged", db)

    decision_id = propose_decision(
        "approve_high_risk_output", a_id, {"output_id": output_id, "entity_id": a_id}, db
    )
    # Use a_id as approver (b_id is the reviewer, a_id is the producer — not the same entity)
    with pytest.raises(GovernanceError, match="UNRESOLVED CHALLENGE"):
        approve_decision(decision_id, b_id, db)
    print("[gov] unresolved challenge blocks high-risk approval ✓")


def test_emergency_shutdown_refuses_high_risk(db, tmp_path, monkeypatch):
    """emergency_shutdown_flag=true refuses a new high-risk action."""
    from civilization.services import governance_service
    from civilization.services.governance_service import propose_decision, GovernanceError

    # Patch controls to set emergency_shutdown_flag=true
    controls_content = (
        "institution_creation_budget: 10\n"
        "duplicate_institution_detector: false\n"
        "unresolved_challenge_blocker: true\n"
        "review_timeout_hours: 48\n"
        "reputation_floor: -2.0\n"
        "emergency_shutdown_flag: true\n"
    )
    ctrl_file = tmp_path / "controls.yaml"
    ctrl_file.write_text(controls_content)
    monkeypatch.setattr(governance_service, "CONTROLS_FILE", ctrl_file)

    with pytest.raises(GovernanceError, match="EMERGENCY SHUTDOWN"):
        propose_decision("approve_high_risk_output", "entity-x", {"output_id": "x"}, db)
    print("[gov] emergency_shutdown_flag blocks high-risk action ✓")


def test_self_authority_expansion_rejected(db):
    """approver_entity_id cannot equal the entity whose authority the decision expands."""
    from civilization.services.governance_service import propose_decision, approve_decision, GovernanceError

    entity_id = f"self-expand-entity-{uuid.uuid4().hex[:6]}"
    decision_id = propose_decision(
        "change_contract", entity_id,
        {"entity_id": entity_id, "change": "expand_scope"},
        db,
    )
    with pytest.raises(GovernanceError, match="SELF-AUTHORITY-EXPANSION REJECTED"):
        approve_decision(decision_id, entity_id, db)
    print("[gov] self-authority-expansion correctly rejected ✓")
