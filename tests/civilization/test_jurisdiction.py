from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
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
            "delegated_authorities", "authority_revocations", "authority_grants", "jurisdictions",
            "society_reputation_snapshots", "society_memory_events", "society_governance_decisions",
            "society_contracts", "society_institution_edges", "societies",
            "agent_membership_edges", "institution_contracts", "institution_output_reviews",
            "civilization_memory_events", "governance_decisions", "departments", "institutions",
        ]:
            cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
        cur.execute((ROOT / "reserve/migrations/006_civilization.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/007_society.sql").read_text())
        cur.execute((ROOT / "reserve/migrations/008_jurisdiction.sql").read_text())
    yield conn
    conn.close()


def _inst(db) -> str:
    from civilization.services.institution_service import create_institution

    name = f"Jurisdiction-{uuid.uuid4().hex[:6]}"
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


def _grant(db, inst_id: str, **kwargs) -> str:
    from civilization.services.jurisdiction_service import grant_jurisdiction

    now = datetime.now(timezone.utc)
    return grant_jurisdiction(
        entity_type="institution",
        entity_id=inst_id,
        allowed_action=kwargs.get("action", "produce"),
        allowed_output_type=kwargs.get("output_type", "software_artifact"),
        granted_by="governance",
        valid_from=kwargs.get("valid_from", now - timedelta(minutes=1)),
        valid_until=kwargs.get("valid_until", now + timedelta(days=1)),
        reputation_requirement=kwargs.get("reputation_requirement"),
        external_review_required=kwargs.get("external_review_required", False),
        constraints={},
        db=db,
    )


def test_allowed_action_succeeds_and_out_of_scope_rejected(db) -> None:
    from civilization.services.jurisdiction_service import JurisdictionError, check_authority

    inst_id = _inst(db)
    _grant(db, inst_id)
    assert check_authority("institution", inst_id, "produce", "software_artifact", db)
    with pytest.raises(JurisdictionError, match="out-of-scope"):
        check_authority("institution", inst_id, "approve_security", "security_approval", db)


def test_expired_and_low_reputation_authority_rejected(db) -> None:
    from civilization.services.jurisdiction_service import JurisdictionError, check_authority

    inst_id = _inst(db)
    _grant(db, inst_id, valid_until=datetime.now(timezone.utc) - timedelta(minutes=1))
    with pytest.raises(JurisdictionError, match="out-of-scope"):
        check_authority("institution", inst_id, "produce", "software_artifact", db)

    inst_low = _inst(db)
    _grant(db, inst_low, reputation_requirement=0.5)
    with pytest.raises(JurisdictionError, match="low reputation"):
        check_authority("institution", inst_low, "produce", "software_artifact", db)


def test_self_granted_rejected_and_delegated_authority_works(db) -> None:
    from civilization.services.jurisdiction_service import JurisdictionError, delegate_authority, grant_jurisdiction

    inst_id = _inst(db)
    now = datetime.now(timezone.utc)
    with pytest.raises(JurisdictionError, match="self-granted"):
        grant_jurisdiction(
            entity_type="institution",
            entity_id=inst_id,
            allowed_action="produce",
            allowed_output_type="software_artifact",
            granted_by=inst_id,
            valid_from=now,
            valid_until=now + timedelta(days=1),
            reputation_requirement=None,
            external_review_required=False,
            constraints={},
            db=db,
        )
    parent = _grant(db, inst_id)
    delegated = delegate_authority(parent, "institution", "delegatee", "produce", "software_artifact", now, now + timedelta(days=1), db)
    assert delegated


def test_jurisdiction_failure_writes_memory(db) -> None:
    from civilization.services.jurisdiction_service import JurisdictionError, check_authority

    inst_id = _inst(db)
    with pytest.raises(JurisdictionError):
        check_authority("institution", inst_id, "allocate_budget", "budget", db)
    with db.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM civilization_memory_events WHERE entity_id = %s AND event_type = 'failure_recorded'",
            (inst_id,),
        )
        assert cur.fetchone()[0] == 1
