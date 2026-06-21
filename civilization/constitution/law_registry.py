"""
Law Registry — maintain the collection of laws (civilization-level and society-level).
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


def register_law(
    law_type: str,
    rule_json: dict,
    civilization_id: Optional[str] = None,
    society_id: Optional[str] = None,
    created_by_decision_id: Optional[str] = None,
    db=None,
) -> dict:
    """
    Register a new law in the law registry.
    Must specify either civilization_id or society_id (or both for civilization-wide adoption).
    """
    if civilization_id is None and society_id is None:
        raise ValueError("Must specify civilization_id or society_id")

    law_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO laws (id, civilization_id, society_id, law_type, rule_json, status, created_by_decision_id, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s, %s)
            """,
            (law_id, civilization_id, society_id, law_type, json.dumps(rule_json), "active", created_by_decision_id, now),
        )

    return {
        "id": law_id,
        "law_type": law_type,
        "rule": rule_json,
        "civilization_id": civilization_id,
        "society_id": society_id,
        "status": "active",
        "created_by_decision_id": created_by_decision_id,
        "created_at": now.isoformat(),
    }


def get_law(law_id: str, db) -> Optional[dict]:
    """Retrieve a law by ID."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, law_type, rule_json, civilization_id, society_id, status, created_at FROM laws WHERE id = %s",
            (law_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "law_type": row[1],
        "rule": row[2],
        "civilization_id": row[3],
        "society_id": row[4],
        "status": row[5],
        "created_at": row[6].isoformat() if row[6] else None,
    }


def list_civilization_laws(civilization_id: str, db, status: Optional[str] = None) -> list[dict]:
    """List all laws for a civilization."""
    query = "SELECT id, law_type, rule_json, status, created_at FROM laws WHERE civilization_id = %s"
    params = [civilization_id]

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "law_type": row[1],
            "rule": row[2],
            "status": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


def list_society_laws(society_id: str, db, status: Optional[str] = None) -> list[dict]:
    """List all laws for a society."""
    query = "SELECT id, law_type, rule_json, status, created_at FROM laws WHERE society_id = %s"
    params = [society_id]

    if status:
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "law_type": row[1],
            "rule": row[2],
            "status": row[3],
            "created_at": row[4].isoformat() if row[4] else None,
        }
        for row in rows
    ]


def retire_law(law_id: str, db) -> None:
    """Retire (deactivate) a law."""
    with db.cursor() as cur:
        cur.execute(
            "UPDATE laws SET status = 'retired' WHERE id = %s",
            (law_id,),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Law {law_id} not found")
