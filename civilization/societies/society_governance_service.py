"""
Society Governance Service — operations for society governance decisions.

Societies make decisions through a voting/approval mechanism among their members.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .society_service import get_society_members, admit_institution, _audit_log


def propose_admission(
    society_id: str,
    institution_id: str,
    proposed_by: str,
    db=None,
) -> dict:
    """Propose admission of an institution to a society."""
    proposal_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_governance_proposals (id, society_id, proposal_type, subject_id, proposed_by, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (proposal_id, society_id, "admission", institution_id, proposed_by, "open", now),
        )

    return {
        "proposal_id": proposal_id,
        "society_id": society_id,
        "proposal_type": "admission",
        "subject_id": institution_id,
        "proposed_by": proposed_by,
        "status": "open",
        "created_at": now.isoformat(),
    }


def get_active_proposals(society_id: str, db) -> list[dict]:
    """Get all open (non-resolved) proposals for a society."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, proposal_type, subject_id, proposed_by, status, created_at
            FROM society_governance_proposals
            WHERE society_id = %s AND status = 'open'
            ORDER BY created_at DESC
            """,
            (society_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "proposal_id": row[0],
            "proposal_type": row[1],
            "subject_id": row[2],
            "proposed_by": row[3],
            "status": row[4],
            "created_at": row[5].isoformat() if row[5] else None,
        }
        for row in rows
    ]


def approve_proposal(
    society_id: str,
    proposal_id: str,
    approved_by: str,
    db=None,
) -> dict:
    """Approve (and execute) a proposal."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT proposal_type, subject_id FROM society_governance_proposals WHERE id = %s AND society_id = %s",
            (proposal_id, society_id),
        )
        row = cur.fetchone()

    if row is None:
        raise ValueError(f"Proposal {proposal_id} not found")

    proposal_type, subject_id = row

    # Execute based on proposal type
    if proposal_type == "admission":
        admit_institution(society_id, subject_id, "member", db)

    # Mark proposal as approved
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE society_governance_proposals
            SET status = 'approved', approved_by = %s, approved_at = %s
            WHERE id = %s
            """,
            (approved_by, now, proposal_id),
        )
        _audit_log(db, society_id, "proposal_approved", {"proposal_id": proposal_id, "type": proposal_type})

    return {
        "proposal_id": proposal_id,
        "status": "approved",
        "approved_by": approved_by,
        "approved_at": now.isoformat(),
    }


def reject_proposal(society_id: str, proposal_id: str, reason: str, db=None) -> dict:
    """Reject a proposal."""
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE society_governance_proposals
            SET status = 'rejected', rejection_reason = %s, updated_at = %s
            WHERE id = %s AND society_id = %s
            """,
            (reason, now, proposal_id, society_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Proposal {proposal_id} not found")

        _audit_log(db, society_id, "proposal_rejected", {"proposal_id": proposal_id, "reason": reason})

    return {
        "proposal_id": proposal_id,
        "status": "rejected",
        "rejection_reason": reason,
        "updated_at": now.isoformat(),
    }


def can_society_judge_dispute(society_id: str, dispute_id: str, db) -> bool:
    """
    Check if a society can judge a dispute.
    A society cannot judge a dispute where the society itself is a defendant.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT defendant_id FROM disputes WHERE id = %s AND dispute_type = 'inter_institution'
            """,
            (dispute_id,),
        )
        row = cur.fetchone()

    if row is None:
        return False

    defendant_id = row[0]

    # Check if society_id matches defendant (societies identified by their ID)
    # For now, a simple check: if the defendant is a society, and it's this society, cannot judge
    # This requires checking if defendant_id is in our societies table
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM societies WHERE id = %s",
            (defendant_id,),
        )
        is_defendant = cur.fetchone() is not None

    return not is_defendant if is_defendant else True


def resolve_inter_institution_dispute(
    society_id: str,
    dispute_id: str,
    ruling: str,
    evidence_ref: str,
    db=None,
) -> dict:
    """
    Society judges an inter-institution dispute and issues a ruling.
    Requires that the society is not the defendant.
    """
    if not can_society_judge_dispute(society_id, dispute_id, db):
        raise ValueError("Society cannot judge dispute where it is the defendant")

    ruling_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dispute_rulings (id, dispute_id, ruling, evidence_ref, issued_by_entity_id, issued_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (ruling_id, dispute_id, ruling, evidence_ref, society_id, now),
        )
        _audit_log(db, society_id, "dispute_resolved", {"dispute_id": dispute_id, "ruling": ruling})

    return {
        "ruling_id": ruling_id,
        "dispute_id": dispute_id,
        "ruling": ruling,
        "issued_by": society_id,
        "issued_at": now.isoformat(),
    }
