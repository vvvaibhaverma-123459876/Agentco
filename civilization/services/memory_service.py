"""
Civilization layer — Memory service.

Query functions for civilization_memory_events scoped by entity type.
"""
from __future__ import annotations

from typing import Optional


def get_agent_memory(agent_id: str, db, event_type: Optional[str] = None) -> list[dict]:
    """Return memory events for an agent (via membership edges → departments → institutions)."""
    sql = (
        "SELECT id, entity_type, entity_id, event_type, summary, evidence_refs, created_at "
        "FROM civilization_memory_events WHERE entity_id = %s"
    )
    params: list = [agent_id]
    if event_type:
        sql += " AND event_type = %s"
        params.append(event_type)
    sql += " ORDER BY created_at DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def get_department_memory(department_id: str, db, event_type: Optional[str] = None) -> list[dict]:
    """Return memory events for a department entity."""
    sql = (
        "SELECT id, entity_type, entity_id, event_type, summary, evidence_refs, created_at "
        "FROM civilization_memory_events WHERE entity_id = %s"
    )
    params: list = [department_id]
    if event_type:
        sql += " AND event_type = %s"
        params.append(event_type)
    sql += " ORDER BY created_at DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def get_institution_memory(institution_id: str, db, event_type: Optional[str] = None) -> list[dict]:
    """Return memory events for an institution entity."""
    sql = (
        "SELECT id, entity_type, entity_id, event_type, summary, evidence_refs, created_at "
        "FROM civilization_memory_events WHERE entity_id = %s"
    )
    params: list = [institution_id]
    if event_type:
        sql += " AND event_type = %s"
        params.append(event_type)
    sql += " ORDER BY created_at DESC"
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "entity_type": row[1],
        "entity_id": row[2],
        "event_type": row[3],
        "summary": row[4],
        "evidence_refs": row[5],
        "created_at": row[6],
    }
