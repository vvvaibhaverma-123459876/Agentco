"""
Civilization layer — Review state machine.

LEGAL TRANSITIONS (exact per spec):
  proposed → under_review → {challenged | approved | rejected}
  challenged → {approved | rejected}
  {approved | rejected} → archived
  Any other transition raises.

'approved' is reachable ONLY after a reviewer_institution_id ≠ producing_institution_id
row exists with status leading to the review completion.  The DB CHECK already enforces
reviewer ≠ producer.  The state machine enforces that approval requires a completed
external review row.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

# Legal state machine transitions
_TRANSITIONS: dict[str, set[str]] = {
    "proposed":     {"under_review"},
    "under_review": {"challenged", "approved", "rejected"},
    "challenged":   {"approved", "rejected"},
    "approved":     {"archived"},
    "rejected":     {"archived"},
    "archived":     set(),
}


class ReviewTransitionError(ValueError):
    pass


def create_review(
    output_id: str,
    producing_institution_id: str,
    reviewer_institution_id: str,
    db,
) -> str:
    """Open a new review (status='proposed'). Returns review_id."""
    if producing_institution_id == reviewer_institution_id:
        raise ReviewTransitionError(
            "Self-certification banned: reviewer must differ from producer"
        )
    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO institution_output_reviews
                (id, output_id, producing_institution_id, reviewer_institution_id,
                 status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 'proposed', %s, %s)
            """,
            (review_id, output_id, producing_institution_id, reviewer_institution_id, now, now),
        )
    _write_memory_event(
        entity_type="institution", entity_id=producing_institution_id,
        event_type="output_created",
        summary=f"Output '{output_id}' proposed for review",
        evidence_refs={"output_id": output_id, "review_id": review_id},
        db=db,
    )
    return review_id


def transition_review(review_id: str, new_status: str, db, evidence: Optional[dict] = None) -> None:
    """Advance a review to new_status.  Raises ReviewTransitionError on illegal transition."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT status, producing_institution_id, reviewer_institution_id, output_id "
            "FROM institution_output_reviews WHERE id = %s",
            (review_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ReviewTransitionError(f"Review {review_id} not found")

    current_status, producing_id, reviewer_id, output_id = row

    allowed = _TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ReviewTransitionError(
            f"Illegal transition: {current_status!r} → {new_status!r}. "
            f"Allowed from {current_status!r}: {sorted(allowed) or 'none (terminal)'}"
        )

    # 'approved' requires that the review was done by an external institution
    # (DB CHECK already enforces reviewer ≠ producer; here we enforce that
    # the review actually progressed through under_review, not jumped directly).
    if new_status == "approved" and current_status == "proposed":
        raise ReviewTransitionError(
            "Cannot approve from 'proposed': review must pass through 'under_review' first"
        )

    now = datetime.now(timezone.utc)
    evidence_json = json.dumps(evidence or {})
    with db.cursor() as cur:
        cur.execute(
            "UPDATE institution_output_reviews SET status = %s, review_evidence = %s::jsonb, "
            "updated_at = %s WHERE id = %s",
            (new_status, evidence_json, now, review_id),
        )

    # Write memory events
    if new_status == "under_review":
        _write_memory_event(
            entity_type="institution", entity_id=reviewer_id,
            event_type="review_completed",
            summary=f"Review of output '{output_id}' entered under_review",
            evidence_refs={"review_id": review_id},
            db=db,
        )
    elif new_status == "challenged":
        _write_memory_event(
            entity_type="institution", entity_id=reviewer_id,
            event_type="challenge_opened",
            summary=f"Review of output '{output_id}' challenged",
            evidence_refs={"review_id": review_id, "evidence": evidence or {}},
            db=db,
        )
    elif new_status in ("approved", "rejected"):
        _write_memory_event(
            entity_type="institution", entity_id=producing_id,
            event_type="review_completed" if new_status == "approved" else "failure_recorded",
            summary=f"Output '{output_id}' review {new_status}",
            evidence_refs={"review_id": review_id},
            db=db,
        )
        if new_status == "challenged":
            _write_memory_event(
                entity_type="institution", entity_id=reviewer_id,
                event_type="challenge_resolved",
                summary=f"Challenge on output '{output_id}' resolved as {new_status}",
                evidence_refs={"review_id": review_id},
                db=db,
            )


def get_review(review_id: str, db) -> Optional[dict]:
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, output_id, producing_institution_id, reviewer_institution_id, "
            "status, review_evidence, reputation_delta FROM institution_output_reviews "
            "WHERE id = %s",
            (review_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "output_id": row[1],
        "producing_institution_id": row[2], "reviewer_institution_id": row[3],
        "status": row[4], "review_evidence": row[5], "reputation_delta": row[6],
    }


def _write_memory_event(
    entity_type: str, entity_id: str, event_type: str,
    summary: str, evidence_refs: dict, db,
    reputation_delta: Optional[float] = None,
) -> str:
    eid = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO civilization_memory_events
                (id, entity_type, entity_id, event_type, summary,
                 evidence_refs, reputation_delta, created_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                eid, entity_type, entity_id, event_type, summary,
                json.dumps(evidence_refs), reputation_delta, now,
            ),
        )
    return eid
