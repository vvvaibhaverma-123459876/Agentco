"""
Civilization Service — manage civilization entities and their society memberships.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


def create_civilization(
    name: str,
    constitution_version: Optional[str] = None,
    db=None,
) -> dict:
    """Create a new civilization."""
    civ_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO civilizations (id, name, constitution_version, status, legitimacy_score, metadata, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (civ_id, name, constitution_version, "active", 0.0, json.dumps({}), now, now),
        )

    return {
        "id": civ_id,
        "name": name,
        "constitution_version": constitution_version,
        "status": "active",
        "legitimacy_score": 0.0,
        "created_at": now.isoformat(),
    }


def get_civilization(civ_id: str, db) -> Optional[dict]:
    """Retrieve a civilization by ID."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, constitution_version, status, legitimacy_score, metadata, created_at, updated_at
            FROM civilizations WHERE id = %s
            """,
            (civ_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "constitution_version": row[2],
        "status": row[3],
        "legitimacy_score": row[4],
        "metadata": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
        "updated_at": row[7].isoformat() if row[7] else None,
    }


def admit_society(civilization_id: str, society_id: str, db=None) -> dict:
    """Admit a society to a civilization."""
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO civilization_society_edges (civilization_id, society_id, membership_status, joined_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (civilization_id, society_id) DO UPDATE SET membership_status = 'active'
            """,
            (civilization_id, society_id, "active", now),
        )

    return {
        "civilization_id": civilization_id,
        "society_id": society_id,
        "membership_status": "active",
        "joined_at": now.isoformat(),
    }


def get_civilization_societies(civilization_id: str, db, active_only: bool = True) -> list[dict]:
    """Get all societies in a civilization."""
    query = """
    SELECT cse.society_id, s.name, s.domain, cse.membership_status, cse.joined_at
    FROM civilization_society_edges cse
    JOIN societies s ON cse.society_id = s.id
    WHERE cse.civilization_id = %s
    """
    params = [civilization_id]

    if active_only:
        query += " AND cse.membership_status = 'active'"

    query += " ORDER BY s.name"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "society_id": row[0],
            "society_name": row[1],
            "society_domain": row[2],
            "membership_status": row[3],
            "joined_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


def activate_emergency_shutdown(civilization_id: str, reason: str, db=None) -> dict:
    """Activate emergency shutdown (blocks high-risk operations)."""
    now = datetime.now(timezone.utc)
    log_id = str(uuid.uuid4())

    with db.cursor() as cur:
        # Record emergency activation
        cur.execute(
            """
            INSERT INTO civilization_emergency_log (id, civilization_id, action, activated_at, reason, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (log_id, civilization_id, "shutdown_activated", now, reason, now),
        )

        # Update civilization status
        cur.execute(
            "UPDATE civilizations SET status = %s, updated_at = %s WHERE id = %s",
            ("emergency", now, civilization_id),
        )

    return {
        "log_id": log_id,
        "civilization_id": civilization_id,
        "action": "shutdown_activated",
        "reason": reason,
        "activated_at": now.isoformat(),
    }


def deactivate_emergency_shutdown(civilization_id: str, db=None) -> dict:
    """Deactivate emergency shutdown (must be explicit)."""
    now = datetime.now(timezone.utc)
    log_id = str(uuid.uuid4())

    with db.cursor() as cur:
        # Record emergency deactivation
        cur.execute(
            """
            INSERT INTO civilization_emergency_log (id, civilization_id, action, activated_at, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (log_id, civilization_id, "shutdown_deactivated", now, now),
        )

        # Update civilization status back to active
        cur.execute(
            "UPDATE civilizations SET status = %s, updated_at = %s WHERE id = %s",
            ("active", now, civilization_id),
        )

    return {
        "log_id": log_id,
        "civilization_id": civilization_id,
        "action": "shutdown_deactivated",
        "deactivated_at": now.isoformat(),
    }


def is_emergency_active(civilization_id: str, db) -> bool:
    """Check if emergency shutdown is currently active."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT status FROM civilizations WHERE id = %s",
            (civilization_id,),
        )
        row = cur.fetchone()

    return row and row[0] == "emergency"
