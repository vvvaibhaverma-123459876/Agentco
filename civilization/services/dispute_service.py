"""Dispute judiciary service."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone


class DisputeError(ValueError):
    pass


def open_dispute(dispute_type: str, plaintiff_id: str, defendant_id: str, db, *, critical: bool = False, source_review_id: str | None = None) -> str:
    dispute_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO disputes
                (id, dispute_type, status, plaintiff_id, defendant_id, critical, source_review_id, created_at, updated_at)
            VALUES (%s, %s, 'opened', %s, %s, %s, %s, %s, %s)
            """,
            (dispute_id, dispute_type, plaintiff_id, defendant_id, critical, source_review_id, now, now),
        )
    return dispute_id


def open_dispute_from_challenge(review_id: str, plaintiff_id: str, defendant_id: str, db, *, critical: bool = False) -> str:
    return open_dispute("output_quality", plaintiff_id, defendant_id, db, critical=critical, source_review_id=review_id)


def submit_evidence(dispute_id: str, submitted_by: str, evidence: dict, db) -> str:
    evidence_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO dispute_evidence (id, dispute_id, submitted_by, evidence) VALUES (%s, %s, %s, %s::jsonb)",
            (evidence_id, dispute_id, submitted_by, json.dumps(evidence)),
        )
        cur.execute("UPDATE disputes SET status = 'evidence_collection', updated_at = %s WHERE id = %s", (datetime.now(timezone.utc), dispute_id))
    return evidence_id


def issue_ruling(dispute_id: str, judge_entity_id: str, ruling: str, penalty: dict, db, *, appeal_window_hours: int = 24) -> str:
    with db.cursor() as cur:
        cur.execute("SELECT plaintiff_id, defendant_id, dispute_type FROM disputes WHERE id = %s", (dispute_id,))
        row = cur.fetchone()
    if not row:
        raise DisputeError("dispute not found")
    plaintiff_id, defendant_id, dispute_type = row
    if judge_entity_id in {plaintiff_id, defendant_id}:
        raise DisputeError("conflicted judge rejected")
    ruling_id = str(uuid.uuid4())
    appeal_deadline = datetime.now(timezone.utc) + timedelta(hours=appeal_window_hours)
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO rulings (id, dispute_id, judge_entity_id, ruling, penalty, appeal_deadline)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            """,
            (ruling_id, dispute_id, judge_entity_id, ruling, json.dumps(penalty), appeal_deadline),
        )
        cur.execute("UPDATE disputes SET status = 'ruled', updated_at = %s WHERE id = %s", (datetime.now(timezone.utc), dispute_id))
    for entity_id, spec in penalty.items():
        _apply_penalty(dispute_id, entity_id, spec, db)
    return ruling_id


def submit_appeal(ruling_id: str, submitted_by: str, reason: str, db) -> str:
    with db.cursor() as cur:
        cur.execute("SELECT dispute_id, appeal_deadline FROM rulings WHERE id = %s", (ruling_id,))
        row = cur.fetchone()
    if not row:
        raise DisputeError("ruling not found")
    dispute_id, appeal_deadline = row
    if datetime.now(timezone.utc) > appeal_deadline:
        raise DisputeError("late appeal rejected")
    appeal_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO appeals (id, ruling_id, submitted_by, reason) VALUES (%s, %s, %s, %s)",
            (appeal_id, ruling_id, submitted_by, reason),
        )
        cur.execute("UPDATE disputes SET status = 'appealed', updated_at = %s WHERE id = %s", (datetime.now(timezone.utc), dispute_id))
    return appeal_id


def finalize_dispute(dispute_id: str, db) -> str:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, d.dispute_type, r.ruling
              FROM rulings r JOIN disputes d ON d.id = r.dispute_id
             WHERE r.dispute_id = %s
             ORDER BY r.created_at DESC LIMIT 1
            """,
            (dispute_id,),
        )
        row = cur.fetchone()
    if not row:
        raise DisputeError("cannot finalize without ruling")
    ruling_id, dispute_type, ruling = row
    precedent_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO precedents (id, ruling_id, dispute_type, summary) VALUES (%s, %s, %s, %s)",
            (precedent_id, ruling_id, dispute_type, ruling),
        )
        cur.execute("UPDATE disputes SET status = 'final', updated_at = %s WHERE id = %s", (datetime.now(timezone.utc), dispute_id))
    return precedent_id


def critical_dispute_blocks_release(output_id: str, db) -> bool:
    with db.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM disputes WHERE source_review_id = %s AND critical = TRUE AND status NOT IN ('final','closed')",
            (output_id,),
        )
        return cur.fetchone() is not None


def _apply_penalty(dispute_id: str, entity_id: str, spec: dict, db) -> None:
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO penalties (id, dispute_id, entity_id, penalty_type, amount) VALUES (%s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), dispute_id, entity_id, spec.get("type", "reputation"), spec.get("amount")),
        )
