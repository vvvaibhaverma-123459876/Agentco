"""Institution-kernel membership lifecycle service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional


VALID_MEMBER_ROLES = frozenset({
    "contributor", "producer", "reviewer", "auditor", "adversary",
    "improver", "lead", "member", "engineer",
})


def add_agent_to_department(
    agent_id: str,
    department_id: str,
    role_name: str,
    db,
    *,
    expires_at: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> None:
    if role_name not in VALID_MEMBER_ROLES:
        raise ValueError(f"Invalid role_name: {role_name}")
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_membership_edges
                (agent_id, department_id, role_name, active, expires_at,
                 deactivated_at, deactivation_reason, evicted_at, eviction_reason,
                 evicted_by, metadata, created_at)
            VALUES (%s, %s, %s, TRUE, %s, NULL, NULL, NULL, NULL, NULL, %s::jsonb, %s)
            ON CONFLICT (agent_id, department_id) DO UPDATE
               SET role_name = EXCLUDED.role_name,
                   active = TRUE,
                   expires_at = EXCLUDED.expires_at,
                   deactivated_at = NULL,
                   deactivation_reason = NULL,
                   evicted_at = NULL,
                   eviction_reason = NULL,
                   evicted_by = NULL,
                   metadata = EXCLUDED.metadata
            """,
            (agent_id, department_id, role_name, expires_at, json.dumps(metadata or {}), now),
        )
        _write_memory_event(
            cur,
            entity_type="department",
            entity_id=department_id,
            event_type="membership_added",
            summary=f"Agent '{agent_id}' added as {role_name}",
            evidence_refs={"agent_id": agent_id, "role_name": role_name},
            created_at=now,
        )


def expire_memberships(db, *, now: Optional[datetime] = None) -> list[tuple[str, str]]:
    now = now or datetime.now(timezone.utc)
    expired: list[tuple[str, str]] = []
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT agent_id, department_id
              FROM agent_membership_edges
             WHERE active = TRUE
               AND expires_at IS NOT NULL
               AND expires_at <= %s
            """,
            (now,),
        )
        rows = cur.fetchall()
        for agent_id, department_id in rows:
            cur.execute(
                """
                UPDATE agent_membership_edges
                   SET active = FALSE,
                       deactivated_at = %s,
                       deactivation_reason = 'expired'
                 WHERE agent_id = %s AND department_id = %s
                """,
                (now, agent_id, department_id),
            )
            _write_memory_event(
                cur,
                entity_type="department",
                entity_id=department_id,
                event_type="membership_expired",
                summary=f"Agent '{agent_id}' membership expired",
                evidence_refs={"agent_id": agent_id},
                created_at=now,
            )
            expired.append((agent_id, department_id))
    return expired


def evict_agent(agent_id: str, department_id: str, reason: str, evicted_by: str, db) -> None:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE agent_membership_edges
               SET active = FALSE,
                   deactivated_at = %s,
                   deactivation_reason = 'evicted',
                   evicted_at = %s,
                   eviction_reason = %s,
                   evicted_by = %s
             WHERE agent_id = %s AND department_id = %s
            """,
            (now, now, reason, evicted_by, agent_id, department_id),
        )
        if cur.rowcount == 0:
            raise ValueError("membership not found")
        _write_memory_event(
            cur,
            entity_type="department",
            entity_id=department_id,
            event_type="membership_evicted",
            summary=f"Agent '{agent_id}' evicted",
            evidence_refs={"agent_id": agent_id, "reason": reason, "evicted_by": evicted_by},
            created_at=now,
        )


def list_active_memberships(department_id: str, db) -> list[dict]:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT agent_id, department_id, role_name, expires_at, metadata
              FROM agent_membership_edges
             WHERE department_id = %s
               AND active = TRUE
               AND evicted_at IS NULL
               AND (expires_at IS NULL OR expires_at > %s)
             ORDER BY agent_id
            """,
            (department_id, now),
        )
        return [
            {
                "agent_id": row[0],
                "department_id": row[1],
                "role_name": row[2],
                "expires_at": row[3],
                "metadata": row[4],
            }
            for row in cur.fetchall()
        ]


def _write_memory_event(cur, *, entity_type: str, entity_id: str, event_type: str, summary: str, evidence_refs: dict, created_at: datetime) -> None:
    cur.execute(
        """
        INSERT INTO civilization_memory_events
            (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
        VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
        """,
        (str(uuid.uuid4()), entity_type, entity_id, event_type, summary, json.dumps(evidence_refs), created_at),
    )
