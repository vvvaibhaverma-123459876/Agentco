"""
Society Service — operations for creating and managing multi-institution societies.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .society_model import Society, SocietyMembership


def create_society(
    name: str,
    domain: str,
    purpose: str,
    authority_scope: Optional[list] = None,
    db=None,
) -> Society:
    """Create a new society in the database."""
    society = Society.create(name, domain, purpose, authority_scope)

    if db is not None:
        with db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO societies
                    (id, name, domain, purpose, status, authority_scope,
                     reputation_score, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s, %s)
                """,
                (
                    society.id,
                    society.name,
                    society.domain,
                    society.purpose,
                    society.status,
                    json.dumps(society.authority_scope),
                    society.reputation_score,
                    json.dumps(society.metadata or {}),
                    society.created_at,
                    society.updated_at,
                ),
            )
            _audit_log(db, society.id, "created", {"name": name, "domain": domain})

    return society


def get_society(society_id: str, db) -> Optional[Society]:
    """Retrieve a society by ID."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, domain, purpose, status, authority_scope,
                   reputation_score, constitution_ref, metadata, created_at, updated_at
            FROM societies WHERE id = %s
            """,
            (society_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return Society(
        id=row[0],
        name=row[1],
        domain=row[2],
        purpose=row[3],
        status=row[4],
        authority_scope=row[5] or [],
        reputation_score=row[6],
        constitution_ref=row[7],
        metadata=row[8],
        created_at=row[9],
        updated_at=row[10],
    )


def list_societies(db, status: Optional[str] = None) -> list[Society]:
    """List all societies, optionally filtered by status."""
    query = "SELECT id, name, domain, purpose, status, authority_scope, reputation_score, constitution_ref, metadata, created_at, updated_at FROM societies"
    params = []
    if status:
        query += " WHERE status = %s"
        params.append(status)
    query += " ORDER BY name"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        Society(
            id=row[0],
            name=row[1],
            domain=row[2],
            purpose=row[3],
            status=row[4],
            authority_scope=row[5] or [],
            reputation_score=row[6],
            constitution_ref=row[7],
            metadata=row[8],
            created_at=row[9],
            updated_at=row[10],
        )
        for row in rows
    ]


def admit_institution(
    society_id: str,
    institution_id: str,
    role: str = "member",
    db=None,
) -> SocietyMembership:
    """Admit an institution to a society (requires governance decision)."""
    # Check if already admitted
    with db.cursor() as cur:
        cur.execute(
            "SELECT membership_status FROM society_institution_edges WHERE society_id = %s AND institution_id = %s",
            (society_id, institution_id),
        )
        existing = cur.fetchone()
        if existing and existing[0] in ("active", "proposed"):
            raise ValueError(f"Institution {institution_id} is already {existing[0]} in society {society_id}")

    now = datetime.now(timezone.utc)
    membership = SocietyMembership(
        society_id=society_id,
        institution_id=institution_id,
        membership_status="active",
        role=role,
        joined_at=now,
    )

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_institution_edges (society_id, institution_id, membership_status, role, joined_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (society_id, institution_id) DO UPDATE
            SET membership_status = EXCLUDED.membership_status, role = EXCLUDED.role
            """,
            (society_id, institution_id, "active", role, now),
        )
        _audit_log(db, society_id, "institution_admitted", {"institution_id": institution_id, "role": role})

    return membership


def retire_institution(society_id: str, institution_id: str, db=None) -> None:
    """Retire an institution from a society."""
    with db.cursor() as cur:
        cur.execute(
            "UPDATE society_institution_edges SET membership_status = 'retired' WHERE society_id = %s AND institution_id = %s",
            (society_id, institution_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Membership not found for {institution_id} in {society_id}")
        _audit_log(db, society_id, "institution_retired", {"institution_id": institution_id})


def suspend_institution_from_society(society_id: str, institution_id: str, db=None) -> None:
    """Suspend an institution from a society (reversible)."""
    with db.cursor() as cur:
        cur.execute(
            "UPDATE society_institution_edges SET membership_status = 'suspended' WHERE society_id = %s AND institution_id = %s",
            (society_id, institution_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Membership not found for {institution_id} in {society_id}")
        _audit_log(db, society_id, "institution_suspended", {"institution_id": institution_id})


def get_society_members(society_id: str, db, active_only: bool = True) -> list[dict]:
    """Get all members (institutions) of a society."""
    query = """
    SELECT sie.institution_id, sie.role, sie.membership_status, sie.joined_at, i.name
    FROM society_institution_edges sie
    JOIN institutions i ON sie.institution_id = i.id
    WHERE sie.society_id = %s
    """
    params = [society_id]

    if active_only:
        query += " AND sie.membership_status = 'active'"

    query += " ORDER BY i.name"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "institution_id": row[0],
            "role": row[1],
            "membership_status": row[2],
            "joined_at": row[3].isoformat() if row[3] else None,
            "institution_name": row[4],
        }
        for row in rows
    ]


def assign_external_reviewer(
    society_id: str,
    institution_id: str,
    reviewer_institution_id: str,
    db=None,
) -> dict:
    """
    Assign an external reviewer from a different institution.
    Reviewer institution must be in the same society.
    """
    if institution_id == reviewer_institution_id:
        raise ValueError("reviewer_institution_id must differ from institution_id (no self-review)")

    # Check both are in society
    with db.cursor() as cur:
        cur.execute(
            "SELECT institution_id FROM society_institution_edges WHERE society_id = %s AND institution_id IN (%s, %s)",
            (society_id, institution_id, reviewer_institution_id),
        )
        members = cur.fetchall()

    if len(members) < 2:
        raise ValueError(f"Both institutions must be active members of society {society_id}")

    return {
        "society_id": society_id,
        "institution_id": institution_id,
        "reviewer_institution_id": reviewer_institution_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }


def _audit_log(db, society_id: str, action: str, details: dict) -> None:
    """Write an audit log entry for a society action."""
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_audit_log (id, society_id, action, details, created_at)
            VALUES (%s, %s, %s, %s::jsonb, %s)
            """,
            (str(uuid.uuid4()), society_id, action, json.dumps(details), datetime.now(timezone.utc)),
        )
