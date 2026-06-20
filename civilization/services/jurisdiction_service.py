"""Jurisdiction and delegated authority checks."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone


class JurisdictionError(ValueError):
    pass


def grant_jurisdiction(
    *,
    entity_type: str,
    entity_id: str,
    allowed_action: str,
    allowed_output_type: str,
    granted_by: str,
    valid_from: datetime,
    valid_until: datetime | None,
    reputation_requirement: float | None,
    external_review_required: bool,
    constraints: dict | None,
    db,
) -> str:
    if granted_by == entity_id:
        raise JurisdictionError("self-granted authority rejected")
    jurisdiction_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO jurisdictions
                (id, entity_type, entity_id, allowed_action, allowed_output_type, constraints,
                 granted_by, valid_from, valid_until, reputation_requirement, external_review_required)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
            """,
            (
                jurisdiction_id,
                entity_type,
                entity_id,
                allowed_action,
                allowed_output_type,
                json.dumps(constraints or {}),
                granted_by,
                valid_from,
                valid_until,
                reputation_requirement,
                external_review_required,
            ),
        )
    return jurisdiction_id


def delegate_authority(
    parent_jurisdiction_id: str,
    delegated_to_entity_type: str,
    delegated_to_entity_id: str,
    allowed_action: str,
    allowed_output_type: str,
    valid_from: datetime,
    valid_until: datetime | None,
    db,
    constraints: dict | None = None,
) -> str:
    delegated_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT allowed_action, allowed_output_type FROM jurisdictions WHERE id = %s
            """,
            (parent_jurisdiction_id,),
        )
        parent = cur.fetchone()
        if not parent:
            raise JurisdictionError("parent jurisdiction not found")
        if parent[0] != allowed_action or parent[1] != allowed_output_type:
            raise JurisdictionError("delegated authority exceeds parent scope")
        cur.execute(
            """
            INSERT INTO delegated_authorities
                (id, parent_jurisdiction_id, delegated_to_entity_type, delegated_to_entity_id,
                 allowed_action, allowed_output_type, constraints, valid_from, valid_until)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (
                delegated_id,
                parent_jurisdiction_id,
                delegated_to_entity_type,
                delegated_to_entity_id,
                allowed_action,
                allowed_output_type,
                json.dumps(constraints or {}),
                valid_from,
                valid_until,
            ),
        )
    return delegated_id


def check_authority(entity_type: str, entity_id: str, action: str, output_type: str, db, *, counterparty_id: str | None = None) -> bool:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, valid_from, valid_until, reputation_requirement, external_review_required
              FROM jurisdictions
             WHERE entity_type = %s AND entity_id = %s
               AND allowed_action = %s AND allowed_output_type = %s
            """,
            (entity_type, entity_id, action, output_type),
        )
        rows = cur.fetchall()
        cur.execute(
            """
            SELECT reputation_score FROM institutions WHERE id = %s
            UNION ALL
            SELECT reputation_score FROM societies WHERE id = %s
            LIMIT 1
            """,
            (entity_id, entity_id),
        )
        rep_row = cur.fetchone()
    reputation = float(rep_row[0]) if rep_row and rep_row[0] is not None else None
    for jurisdiction_id, valid_from, valid_until, reputation_requirement, external_review_required in rows:
        if valid_from > now or (valid_until is not None and valid_until < now):
            continue
        if reputation_requirement is not None and (reputation is None or reputation < float(reputation_requirement)):
            _failure(entity_type, entity_id, action, output_type, "low_reputation", db)
            raise JurisdictionError("low reputation authority rejected")
        if counterparty_id and counterparty_id == entity_id:
            _failure(entity_type, entity_id, action, output_type, "conflict_of_interest", db)
            raise JurisdictionError("conflict of interest")
        if external_review_required:
            return True
        return True
    _failure(entity_type, entity_id, action, output_type, "out_of_scope_or_expired", db)
    raise JurisdictionError("out-of-scope or expired authority")


def _failure(entity_type: str, entity_id: str, action: str, output_type: str, reason: str, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO civilization_memory_events
                (id, entity_type, entity_id, event_type, summary, evidence_refs, created_at)
            VALUES (%s, %s, %s, 'failure_recorded', %s, %s::jsonb, %s)
            """,
            (
                str(uuid.uuid4()),
                entity_type,
                entity_id,
                f"Jurisdiction failure: {reason}",
                json.dumps({"action": action, "output_type": output_type, "reason": reason}),
                datetime.now(timezone.utc),
            ),
        )
