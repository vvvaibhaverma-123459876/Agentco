from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 not installed")

DSN = os.environ.get("AGENTCO_TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def db():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    with conn.cursor() as cur:
        for tbl in [
            "society_reputation_snapshots", "society_memory_events", "society_governance_decisions",
            "society_contracts", "society_institution_edges", "societies",
            "agent_membership_edges", "institution_contracts", "institution_output_reviews",
            "civilization_memory_events", "governance_decisions", "departments", "institutions",
        ]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/006_civilization.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/007_society.sql").read_text())
    yield conn
    conn.close()


def _inst(db, name: str) -> str:
    from civilization.services.institution_service import create_institution

    return create_institution(name, {
        "institution_name": name,
        "accepted_inputs": ["a"],
        "produced_outputs": ["b"],
        "verification_required": True,
        "required_external_reviewer": "Other",
        "failure_conditions": ["f"],
        "escalation_target": "governance",
        "reputation_metric": "overall_log_score",
    }, db)["institution_id"]


def test_society_created_and_institution_admitted_through_governance(db) -> None:
    from civilization.services.society_service import admit_institution, create_society

    society_id = create_society("Engineering Society", "engineering", "founder", "external-approver", {}, db)
    inst_id = _inst(db, f"Software-{uuid.uuid4().hex[:4]}")
    decision_id = admit_institution(society_id, inst_id, "founder", "external-approver", db)
    assert decision_id


def test_duplicate_membership_rejected(db) -> None:
    from civilization.services.society_service import SocietyError, admit_institution, create_society

    society_id = create_society("Security Society", "security", "founder", "external-approver", {}, db)
    inst_id = _inst(db, f"Security-{uuid.uuid4().hex[:4]}")
    admit_institution(society_id, inst_id, "founder", "external-approver", db)
    with pytest.raises(SocietyError, match="duplicate"):
        admit_institution(society_id, inst_id, "founder", "external-approver", db)


def test_society_reputation_recomputes_and_unresolved_dispute_blocks_legitimacy(db) -> None:
    from civilization.services.society_service import (
        admit_institution,
        create_society,
        open_dispute,
        recompute_society_reputation,
    )

    society_id = create_society("Reliability Society", "reliability", "founder", "external-approver", {}, db)
    inst_id = _inst(db, f"Reliability-{uuid.uuid4().hex[:4]}")
    admit_institution(society_id, inst_id, "founder", "external-approver", db)
    old_autocommit = db.autocommit
    db.autocommit = False
    try:
        with db.cursor() as cur:
            cur.execute("SET LOCAL civilization.reputation_update_authorized = 'true'")
            cur.execute("UPDATE institutions SET reputation_score = 0.8 WHERE id = %s", (inst_id,))
        db.commit()
    finally:
        db.autocommit = old_autocommit
    open_dispute(society_id, "plaintiff", inst_id, critical=True, db=db)
    result = recompute_society_reputation(society_id, db)
    assert result["society_score"] < 0.8
    assert result["legitimacy_blocked"] is True


def test_low_reputation_loses_high_risk_authority_and_society_cannot_judge_self(db) -> None:
    from civilization.services.society_service import (
        SocietyError,
        create_society,
        low_reputation_blocks_high_risk_authority,
        open_dispute,
    )

    society_id = create_society("Architecture Society", "architecture", "founder", "external-approver", {}, db)
    inst_id = _inst(db, f"Architecture-{uuid.uuid4().hex[:4]}")
    assert low_reputation_blocks_high_risk_authority(society_id, inst_id, 0.1, db) is True
    with pytest.raises(SocietyError, match="defendant"):
        open_dispute(society_id, "plaintiff", society_id, critical=True, db=db)


def test_society_memory_records_events(db) -> None:
    from civilization.services.society_service import admit_institution, create_society, recompute_society_reputation

    society_id = create_society("QA Society", "qa", "founder", "external-approver", {}, db)
    inst_id = _inst(db, f"QA-{uuid.uuid4().hex[:4]}")
    admit_institution(society_id, inst_id, "founder", "external-approver", db)
    recompute_society_reputation(society_id, db)
    with db.cursor() as cur:
        cur.execute("SELECT event_type FROM society_memory_events WHERE society_id = %s", (society_id,))
        events = {r[0] for r in cur.fetchall()}
    assert {"society_created", "institution_admitted", "society_reputation_updated"}.issubset(events)
