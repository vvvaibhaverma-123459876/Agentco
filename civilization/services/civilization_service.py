"""Civilization constitution and law registry service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone


class CivilizationError(ValueError):
    pass


def create_civilization(name: str, proposed_by: str, external_approval_id: str, quorum_count: int, constitution: dict, db) -> str:
    if quorum_count < 2 or not external_approval_id:
        raise CivilizationError("civilization creation requires constitutional governance")
    civ_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute("INSERT INTO civilizations (id, name, status, active_constitution_version_id, created_at, updated_at) VALUES (%s, %s, 'active', %s, %s, %s)", (civ_id, name, version_id, now, now))
        cur.execute(
            """
            INSERT INTO constitution_versions
                (id, civilization_id, version, constitution, adopted, quorum_count, external_approval_id)
            VALUES (%s, %s, 'v1', %s::jsonb, TRUE, %s, %s)
            """,
            (version_id, civ_id, json.dumps(constitution), quorum_count, external_approval_id),
        )
    _memory(civ_id, "constitution_adopted", "Initial constitution adopted", {"version_id": version_id, "proposed_by": proposed_by}, db)
    return civ_id


def admit_society(civilization_id: str, society_id: str, proposed_by: str, external_approval_id: str, quorum_count: int, db) -> str:
    amendment_id = _adopt_amendment(
        civilization_id,
        proposed_by,
        external_approval_id,
        quorum_count,
        {"admit_society": society_id},
        db,
    )
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO civilization_society_edges (civilization_id, society_id, status, admitted_by_amendment_id) VALUES (%s, %s, 'active', %s)",
            (civilization_id, society_id, amendment_id),
        )
    _memory(civilization_id, "society_admitted", "Society admitted through constitutional process", {"society_id": society_id, "amendment_id": amendment_id}, db)
    return amendment_id


def adopt_constitution_version(civilization_id: str, version: str, constitution: dict, proposed_by: str, external_approval_id: str, quorum_count: int, db) -> str:
    _adopt_amendment(civilization_id, proposed_by, external_approval_id, quorum_count, {"constitution_version": version}, db)
    version_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO constitution_versions
                (id, civilization_id, version, constitution, adopted, quorum_count, external_approval_id)
            VALUES (%s, %s, %s, %s::jsonb, TRUE, %s, %s)
            """,
            (version_id, civilization_id, version, json.dumps(constitution), quorum_count, external_approval_id),
        )
        cur.execute("UPDATE civilizations SET active_constitution_version_id = %s, updated_at = %s WHERE id = %s", (version_id, datetime.now(timezone.utc), civilization_id))
    _memory(civilization_id, "constitution_amended", "Constitution version adopted", {"version_id": version_id}, db)
    return version_id


def create_law(civilization_id: str, law_code: str, title: str, body: str, db) -> str:
    with db.cursor() as cur:
        cur.execute("SELECT active_constitution_version_id FROM civilizations WHERE id = %s", (civilization_id,))
        version_id = cur.fetchone()[0]
    law_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO laws (id, civilization_id, law_code, title, body, constitution_version_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (law_id, civilization_id, law_code, title, body, version_id),
        )
    _memory(civilization_id, "law_created", title, {"law_id": law_id}, db)
    return law_id


def declare_emergency(civilization_id: str, reason: str, declared_by: str, valid_until: datetime, db) -> str:
    if valid_until <= datetime.now(timezone.utc):
        raise CivilizationError("emergency powers require future expiry")
    emergency_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO emergency_states (id, civilization_id, reason, declared_by, valid_until) VALUES (%s, %s, %s, %s, %s)",
            (emergency_id, civilization_id, reason, declared_by, valid_until),
        )
    _memory(civilization_id, "emergency_declared", reason, {"emergency_id": emergency_id, "valid_until": valid_until.isoformat()}, db)
    return emergency_id


def high_risk_blocked_by_emergency(civilization_id: str, db) -> bool:
    with db.cursor() as cur:
        cur.execute("SELECT 1 FROM emergency_states WHERE civilization_id = %s AND valid_until > %s", (civilization_id, datetime.now(timezone.utc)))
        return cur.fetchone() is not None


def constitutional_dispute(civilization_id: str, plaintiff_id: str, defendant_id: str, judge_id: str, db) -> str:
    if judge_id in {plaintiff_id, defendant_id}:
        raise CivilizationError("no entity judges its own constitutional dispute")
    _memory(civilization_id, "constitutional_dispute_ruled", "Cross-society constitutional dispute ruled", {"plaintiff_id": plaintiff_id, "defendant_id": defendant_id, "judge_id": judge_id}, db)
    return "binding"


def _adopt_amendment(civilization_id: str, proposed_by: str, external_approval_id: str, quorum_count: int, payload: dict, db) -> str:
    if quorum_count < 2 or not external_approval_id:
        raise CivilizationError("invalid amendment rejected")
    amendment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO constitutional_amendments
                (id, civilization_id, status, proposed_by, external_approval_id, quorum_count, payload, created_at, updated_at)
            VALUES (%s, %s, 'adopted', %s, %s, %s, %s::jsonb, %s, %s)
            """,
            (amendment_id, civilization_id, proposed_by, external_approval_id, quorum_count, json.dumps(payload), now, now),
        )
    _memory(civilization_id, "amendment_adopted", "Constitutional amendment adopted", {"amendment_id": amendment_id}, db)
    return amendment_id


def _memory(civilization_id: str, event_type: str, summary: str, evidence_refs: dict, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO civilization_constitution_memory_events (id, civilization_id, event_type, summary, evidence_refs) VALUES (%s, %s, %s, %s, %s::jsonb)",
            (str(uuid.uuid4()), civilization_id, event_type, summary, json.dumps(evidence_refs)),
        )
