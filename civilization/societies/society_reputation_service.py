"""
Society Reputation Service — aggregate reputation from member institutions.

A society's reputation is computed from the reputations of its active member institutions.
"""
from __future__ import annotations

from typing import Optional


def compute_society_reputation(society_id: str, db) -> float:
    """
    Compute society reputation as the average reputation of active member institutions.
    Returns 0.0 if no active members.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT AVG(i.reputation_score) AS avg_reputation, COUNT(i.id) AS member_count
            FROM society_institution_edges sie
            JOIN institutions i ON sie.institution_id = i.id
            WHERE sie.society_id = %s AND sie.membership_status = 'active' AND i.reputation_score IS NOT NULL
            """,
            (society_id,),
        )
        row = cur.fetchone()

    if row is None or row[0] is None or row[1] == 0:
        return 0.0

    return float(row[0])


def update_society_reputation(society_id: str, db) -> float:
    """
    Recompute and persist the society's reputation score.
    Returns the new score.
    """
    new_score = compute_society_reputation(society_id, db)

    with db.cursor() as cur:
        cur.execute(
            "UPDATE societies SET reputation_score = %s, updated_at = NOW() WHERE id = %s",
            (new_score, society_id),
        )

    return new_score


def get_member_contribution_to_reputation(
    society_id: str,
    institution_id: str,
    db,
) -> Optional[dict]:
    """
    Get the contribution of a specific member institution to society reputation.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.name, i.reputation_score, sie.role, sie.joined_at
            FROM institutions i
            JOIN society_institution_edges sie ON sie.institution_id = i.id
            WHERE sie.society_id = %s AND sie.institution_id = %s AND sie.membership_status = 'active'
            """,
            (society_id, institution_id),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "institution_id": row[0],
        "institution_name": row[1],
        "reputation_score": row[2],
        "role": row[3],
        "joined_at": row[4].isoformat() if row[4] else None,
    }


def aggregate_member_reputations(society_id: str, db) -> dict:
    """
    Get detailed reputation breakdown for all active members of a society.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.name, i.reputation_score, sie.role, sie.joined_at
            FROM institutions i
            JOIN society_institution_edges sie ON sie.institution_id = i.id
            WHERE sie.society_id = %s AND sie.membership_status = 'active'
            ORDER BY i.reputation_score DESC NULLS LAST
            """,
            (society_id,),
        )
        rows = cur.fetchall()

    members = [
        {
            "institution_id": row[0],
            "institution_name": row[1],
            "reputation_score": row[2],
            "role": row[3],
            "joined_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]

    scores = [m["reputation_score"] for m in members if m["reputation_score"] is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    return {
        "society_id": society_id,
        "member_count": len(members),
        "active_member_count": len([m for m in members if m["reputation_score"] is not None]),
        "average_reputation": avg_score,
        "members": members,
    }
