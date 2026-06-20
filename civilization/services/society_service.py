"""Governed Society layer services."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone


class SocietyError(ValueError):
    pass


def create_society(name: str, domain: str, proposer_entity_id: str, approver_entity_id: str, contract: dict, db) -> str:
    if proposer_entity_id == approver_entity_id:
        raise SocietyError("society creation requires independent governance approval")
    society_id = str(uuid.uuid4())
    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_governance_decisions
                (id, decision_type, status, proposer_entity_id, approver_entity_id, payload, created_at, updated_at)
            VALUES (%s, 'create_society', 'executed', %s, %s, %s::jsonb, %s, %s)
            """,
            (decision_id, proposer_entity_id, approver_entity_id, json.dumps({"name": name, "domain": domain}), now, now),
        )
        cur.execute(
            "INSERT INTO societies (id, name, domain, status, created_at, updated_at) VALUES (%s, %s, %s, 'active', %s, %s)",
            (society_id, name, domain, now, now),
        )
        cur.execute(
            "INSERT INTO society_contracts (society_id, contract, created_at) VALUES (%s, %s::jsonb, %s)",
            (society_id, json.dumps(contract), now),
        )
    _memory(society_id, "society_created", f"Society '{name}' created through governance", {"decision_id": decision_id}, db)
    return society_id


def admit_institution(society_id: str, institution_id: str, proposer_entity_id: str, approver_entity_id: str, db) -> str:
    if institution_id == approver_entity_id:
        raise SocietyError("institution cannot approve its own society admission")
    decision_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM society_institution_edges WHERE society_id = %s AND institution_id = %s AND status = 'active'",
            (society_id, institution_id),
        )
        if cur.fetchone():
            raise SocietyError("duplicate society membership rejected")
        cur.execute(
            """
            INSERT INTO society_governance_decisions
                (id, society_id, decision_type, status, proposer_entity_id, approver_entity_id, payload, created_at, updated_at)
            VALUES (%s, %s, 'admit_institution', 'executed', %s, %s, %s::jsonb, %s, %s)
            """,
            (
                decision_id,
                society_id,
                proposer_entity_id,
                approver_entity_id,
                json.dumps({"institution_id": institution_id}),
                now,
                now,
            ),
        )
        cur.execute(
            """
            INSERT INTO society_institution_edges
                (society_id, institution_id, status, admitted_by_decision_id, created_at)
            VALUES (%s, %s, 'active', %s, %s)
            """,
            (society_id, institution_id, decision_id, now),
        )
    _memory(society_id, "institution_admitted", "Institution admitted to society", {"institution_id": institution_id, "decision_id": decision_id}, db)
    return decision_id


def recompute_society_reputation(society_id: str, db) -> dict:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.id, i.reputation_score
              FROM society_institution_edges e
              JOIN institutions i ON i.id = e.institution_id
             WHERE e.society_id = %s AND e.status = 'active'
            """,
            (society_id,),
        )
        rows = cur.fetchall()
        cur.execute(
            """
            SELECT payload FROM society_governance_decisions
             WHERE society_id = %s AND decision_type = 'dispute' AND status <> 'executed'
            """,
            (society_id,),
        )
        unresolved_disputes = cur.fetchall()
        cur.execute(
            """
            SELECT payload FROM society_governance_decisions
             WHERE society_id = %s AND decision_type = 'failure'
            """,
            (society_id,),
        )
        failures = cur.fetchall()

    scores = [float(score) for _, score in rows if score is not None]
    base = sum(scores) / len(scores) if scores else None
    dispute_count = len(unresolved_disputes)
    failure_count = len(failures)
    legitimacy_blocked = dispute_count > 0
    adjusted = None if base is None else base - (0.15 * dispute_count) - (0.05 * failure_count)
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            "UPDATE societies SET reputation_score = %s, legitimacy_blocked = %s, updated_at = %s WHERE id = %s",
            (adjusted, legitimacy_blocked, now, society_id),
        )
        cur.execute(
            """
            INSERT INTO society_reputation_snapshots
                (id, society_id, reputation_score, unresolved_dispute_count, repeated_failure_count, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (str(uuid.uuid4()), society_id, adjusted, dispute_count, failure_count, now),
        )
    _memory(society_id, "society_reputation_updated", "Society reputation recomputed", {"unresolved_disputes": dispute_count}, db)
    return {"society_score": adjusted, "unresolved_disputes": dispute_count, "legitimacy_blocked": legitimacy_blocked}


def open_dispute(society_id: str, plaintiff_id: str, defendant_id: str, critical: bool, db) -> str:
    if society_id == defendant_id:
        raise SocietyError("society cannot judge a dispute where it is defendant")
    dispute_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_governance_decisions
                (id, society_id, decision_type, status, proposer_entity_id, payload, created_at, updated_at)
            VALUES (%s, %s, 'dispute', 'proposed', %s, %s::jsonb, %s, %s)
            """,
            (
                dispute_id,
                society_id,
                plaintiff_id,
                json.dumps({"plaintiff_id": plaintiff_id, "defendant_id": defendant_id, "critical": critical}),
                now,
                now,
            ),
        )
    _memory(society_id, "dispute_opened", "Society dispute opened", {"dispute_id": dispute_id, "defendant_id": defendant_id}, db)
    return dispute_id


def low_reputation_blocks_high_risk_authority(society_id: str, institution_id: str, minimum_score: float, db) -> bool:
    with db.cursor() as cur:
        cur.execute("SELECT reputation_score FROM institutions WHERE id = %s", (institution_id,))
        row = cur.fetchone()
    return row is None or row[0] is None or float(row[0]) < minimum_score


def _memory(society_id: str, event_type: str, summary: str, evidence_refs: dict, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society_memory_events (id, society_id, event_type, summary, evidence_refs, created_at)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            """,
            (str(uuid.uuid4()), society_id, event_type, summary, json.dumps(evidence_refs), datetime.now(timezone.utc)),
        )
