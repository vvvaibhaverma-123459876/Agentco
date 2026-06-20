"""Institution and society lifecycle evolution service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone


class EvolutionError(ValueError):
    pass


def propose_institution(institution_id: str, db) -> None:
    _set_institution_state(institution_id, "proposed", "limited", db)


def start_trial(institution_id: str, approver_id: str, db) -> None:
    if approver_id == institution_id:
        raise EvolutionError("self-admission rejected")
    _set_institution_state(institution_id, "trial", "limited", db)


def activate_after_trial(institution_id: str, approver_id: str, db) -> None:
    if approver_id == institution_id:
        raise EvolutionError("self-admission rejected")
    state = institution_state(institution_id, db)
    if state["lifecycle_state"] != "trial":
        raise EvolutionError("trial period required before active status")
    _set_institution_state(institution_id, "active", "full", db)


def high_risk_allowed(institution_id: str, db) -> bool:
    state = institution_state(institution_id, db)
    return state["lifecycle_state"] == "active" and state["authority_level"] == "full"


def low_reputation_triggers_probation(institution_id: str, reputation_score: float, floor: float, db) -> None:
    if reputation_score < floor:
        _set_institution_state(institution_id, "probation", "limited", db)


def suspend_institution(institution_id: str, reason: str, db) -> None:
    _set_institution_state(institution_id, "suspended", "none", db)
    _event("institution", institution_id, "suspended", reason, {}, db)


def retire_institution(institution_id: str, reason: str, db) -> None:
    _set_institution_state(institution_id, "retired", "none", db)
    _event("institution", institution_id, "retired", reason, {"memory_preserved": True}, db)


def merge_institutions(source_ids: list[str], target_id: str, obligations: dict, db) -> None:
    for source_id in source_ids:
        _event("institution", target_id, "merge_obligation_transferred", "Merge transferred obligations", {"source_id": source_id, "obligations": obligations}, db)


def split_institution(parent_id: str, child_ids: list[str], db) -> None:
    for child_id in child_ids:
        _event("institution", child_id, "split_lineage_preserved", "Split preserved lineage", {"parent_id": parent_id}, db)


def institution_state(institution_id: str, db) -> dict:
    with db.cursor() as cur:
        cur.execute("SELECT lifecycle_state, authority_level FROM institution_lifecycle WHERE institution_id = %s", (institution_id,))
        row = cur.fetchone()
    if not row:
        return {"lifecycle_state": "proposed", "authority_level": "limited"}
    return {"lifecycle_state": row[0], "authority_level": row[1]}


def _set_institution_state(institution_id: str, lifecycle_state: str, authority_level: str, db) -> None:
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO institution_lifecycle (institution_id, lifecycle_state, authority_level, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (institution_id) DO UPDATE
               SET lifecycle_state = EXCLUDED.lifecycle_state,
                   authority_level = EXCLUDED.authority_level,
                   updated_at = EXCLUDED.updated_at
            """,
            (institution_id, lifecycle_state, authority_level, now),
        )
    _event("institution", institution_id, f"lifecycle_{lifecycle_state}", f"Institution moved to {lifecycle_state}", {}, db)


def _event(entity_type: str, entity_id: str, event_type: str, summary: str, evidence_refs: dict, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO lifecycle_events (id, entity_type, entity_id, event_type, summary, evidence_refs) VALUES (%s, %s, %s, %s, %s, %s::jsonb)",
            (str(uuid.uuid4()), entity_type, entity_id, event_type, summary, json.dumps(evidence_refs)),
        )
