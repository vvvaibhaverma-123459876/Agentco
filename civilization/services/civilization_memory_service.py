"""Civilizational memory and lineage service."""
from __future__ import annotations

import json
import uuid


class MemoryError(ValueError):
    pass


def create_precedent_from_final_ruling(ruling_id: str, dispute_type: str, summary: str, db) -> str:
    precedent_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO precedents (id, ruling_id, dispute_type, summary) VALUES (%s, %s, %s, %s)",
            (precedent_id, ruling_id, dispute_type, summary),
        )
    return precedent_id


def extract_lesson(source_event_ids: list[str], lesson: str, db, approved: bool = True) -> str:
    if len(source_event_ids) < 2 and not approved:
        raise MemoryError("lesson requires repeated pattern or approved extraction")
    lesson_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO lessons (id, source_pattern, lesson, approved, source_event_ids) VALUES (%s, %s, %s, %s, %s::jsonb)",
            (lesson_id, "repeated_failure" if len(source_event_ids) > 1 else "approved_extraction", lesson, approved, json.dumps(source_event_ids)),
        )
    return lesson_id


def summarize_memory(raw_event_refs: list[str], summary: str, db) -> str:
    if not raw_event_refs:
        raise MemoryError("memory summary must link to raw events")
    summary_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO memory_summaries (id, summary, raw_event_refs) VALUES (%s, %s, %s::jsonb)",
            (summary_id, summary, json.dumps(raw_event_refs)),
        )
    return summary_id


def record_genealogy(entity_type: str, entity_id: str, event_type: str, db, *, parent_entity_id: str | None = None, obligations: dict | None = None) -> str:
    genealogy_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO entity_genealogy (id, entity_type, entity_id, parent_entity_id, event_type, obligations) VALUES (%s, %s, %s, %s, %s, %s::jsonb)",
            (genealogy_id, entity_type, entity_id, parent_entity_id, event_type, json.dumps(obligations or {})),
        )
    return genealogy_id


def record_trust_lineage(claim_id: str, db, *, agent_id: str | None = None, institution_id: str | None = None, society_id: str | None = None, civilization_id: str | None = None, source_refs: list[str] | None = None) -> str:
    lineage_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO trust_lineage
                (id, claim_id, agent_id, institution_id, society_id, civilization_id, source_refs)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            """,
            (lineage_id, claim_id, agent_id, institution_id, society_id, civilization_id, json.dumps(source_refs or [])),
        )
    return lineage_id


def inject_memory_without_authority_change(summary: str, db) -> str:
    return summarize_memory(["manual-note"], summary, db)
