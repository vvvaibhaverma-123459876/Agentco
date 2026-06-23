"""
Civilization layer — Governance service.

Rules (exact per spec):
  - approver_entity_id MUST differ from the entity whose authority the decision expands.
  - Every status change writes an audit-log entry (decision_log) and sets audit_event_id.
  - Anti-chaos controls from civilization/controls.yaml are enforced here.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
import psycopg2

from .controls_cache import ControlsCache

CONTROLS_FILE = Path(__file__).resolve().parents[1] / "controls.yaml"
_controls_cache = ControlsCache(CONTROLS_FILE)

VALID_TYPES = frozenset([
    "create_institution", "retire_institution", "approve_high_risk_output",
    "change_reputation_weights", "change_contract",
])
VALID_STATUSES = frozenset([
    "proposed", "deliberating", "approved", "rejected", "executed", "rolled_back",
])
_STATUS_TRANSITIONS = {
    "proposed":     {"deliberating", "approved", "rejected"},
    "deliberating": {"approved", "rejected"},
    "approved":     {"executed", "rolled_back"},
    "rejected":     set(),
    "executed":     {"rolled_back"},
    "rolled_back":  set(),
}


class GovernanceError(ValueError):
    pass


def _load_controls() -> dict:
    """Load controls from cache (auto-reloads on file change)."""
    return _controls_cache.get()


def propose_decision(
    decision_type: str,
    proposer_entity_id: str,
    payload: dict,
    db,
) -> str:
    """Create a governance_decisions row with status='proposed'. Returns decision_id."""
    try:
        if decision_type not in VALID_TYPES:
            raise GovernanceError(f"Unknown decision_type: {decision_type}")
        controls = _load_controls()

        # Emergency shutdown blocks new high-risk actions
        if controls.get("emergency_shutdown_flag") and decision_type == "approve_high_risk_output":
            raise GovernanceError(
                "EMERGENCY SHUTDOWN: emergency_shutdown_flag=true — new high-risk actions refused"
            )

        # Duplicate institution detector — check name+purpose (purpose defaults to name)
        if decision_type == "create_institution" and controls.get("duplicate_institution_detector"):
            name = payload.get("name", "")
            purpose = payload.get("purpose") or name
            try:
                with db.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM institutions WHERE name = %s AND status = 'active'",
                        (name,),
                    )
                    if cur.fetchone():
                        raise GovernanceError(
                            f"DUPLICATE INSTITUTION: active institution with name='{name}' already exists"
                        )
            except psycopg2.DatabaseError as e:
                db.rollback()
                raise GovernanceError(f"Database error during duplicate check: {e}")

        decision_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        audit_id = _write_audit_entry(
            summary=f"governance_decision proposed: type={decision_type}",
            payload=payload, db=db,
        )
        try:
            with db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO governance_decisions
                        (id, decision_type, status, proposer_entity_id, payload,
                         audit_event_id, created_at, updated_at)
                    VALUES (%s, %s, 'proposed', %s, %s::jsonb, %s, %s, %s)
                    """,
                    (decision_id, decision_type, proposer_entity_id,
                     json.dumps(payload), audit_id, now, now),
                )
            db.commit()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error during decision creation: {e}")
        return decision_id
    except GovernanceError:
        raise
    except Exception as e:
        db.rollback()
        raise GovernanceError(f"Unexpected error in propose_decision: {e}")


def approve_decision(
    decision_id: str,
    approver_entity_id: str,
    db,
) -> None:
    """
    Approve a governance decision.
    RULE: approver_entity_id MUST differ from the entity whose authority the decision expands.
    """
    try:
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT decision_type, status, proposer_entity_id, payload "
                    "FROM governance_decisions WHERE id = %s FOR UPDATE",
                    (decision_id,),
                )
                row = cur.fetchone()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error fetching decision: {e}")

        if row is None:
            raise GovernanceError(f"Decision {decision_id} not found")
        decision_type, current_status, proposer_id, payload_raw = row
        payload = payload_raw if isinstance(payload_raw, dict) else json.loads(payload_raw)

        # Self-authority-expansion check
        affected_entity = payload.get("entity_id") or proposer_id
        if approver_entity_id == affected_entity:
            raise GovernanceError(
                f"SELF-AUTHORITY-EXPANSION REJECTED: approver ({approver_entity_id}) "
                f"cannot approve a decision that expands its own authority"
            )

        # Unresolved challenge blocker for high-risk outputs
        if decision_type == "approve_high_risk_output":
            controls = _load_controls()
            if controls.get("unresolved_challenge_blocker"):
                output_id = payload.get("output_id")
                if output_id:
                    try:
                        with db.cursor() as cur:
                            cur.execute(
                                "SELECT id FROM institution_output_reviews "
                                "WHERE output_id = %s AND status = 'challenged'",
                                (output_id,),
                            )
                            if cur.fetchone():
                                raise GovernanceError(
                                    f"UNRESOLVED CHALLENGE: output '{output_id}' has an open "
                                    "challenged review — cannot approve high-risk output"
                                )
                    except psycopg2.DatabaseError as e:
                        db.rollback()
                        raise GovernanceError(f"Database error checking challenges: {e}")

        _transition_decision(decision_id, "approved", approver_entity_id, db)
    except GovernanceError:
        raise
    except Exception as e:
        db.rollback()
        raise GovernanceError(f"Unexpected error in approve_decision: {e}")


def _transition_decision(decision_id: str, new_status: str, actor_id: str, db) -> None:
    try:
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT status FROM governance_decisions WHERE id = %s FOR UPDATE",
                    (decision_id,),
                )
                row = cur.fetchone()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error fetching decision status: {e}")

        if row is None:
            raise GovernanceError(f"Decision {decision_id} not found")
        current = row[0]
        allowed = _STATUS_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise GovernanceError(
                f"Illegal governance transition: {current!r} → {new_status!r}"
            )
        now = datetime.now(timezone.utc)
        audit_id = _write_audit_entry(
            summary=f"governance_decision {decision_id} → {new_status} by {actor_id}",
            payload={"decision_id": decision_id, "new_status": new_status, "actor": actor_id},
            db=db,
        )
        try:
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE governance_decisions SET status = %s, approver_entity_id = %s, "
                    "audit_event_id = %s, updated_at = %s WHERE id = %s",
                    (new_status, actor_id, audit_id, now, decision_id),
                )
            db.commit()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error updating decision status: {e}")
    except GovernanceError:
        raise
    except Exception as e:
        db.rollback()
        raise GovernanceError(f"Unexpected error in _transition_decision: {e}")


def _write_audit_entry(summary: str, payload: dict, db) -> str:
    """Write a row to decision_log (the existing audit-log table). Returns log_id (uuid)."""
    try:
        import hashlib
        entry_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        # Real decision_log schema (migration 004 + 012):
        #   log_id uuid, agent_id varchar, action_type varchar, input_summary text,
        #   output_summary text, confidence_score numeric, risk_level varchar,
        #   human_approved boolean, timestamp timestamptz, chain_hash text, prev_hash text
        try:
            with db.cursor() as cur:
                cur.execute(
                    "SELECT chain_hash FROM decision_log ORDER BY timestamp DESC LIMIT 1"
                )
                prev_row = cur.fetchone()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error reading audit log: {e}")

        prev_hash = prev_row[0] if prev_row else ("0" * 64)
        canonical = f"{entry_id}|governance|governance_decision|{summary}|{prev_hash}"
        chain_hash = hashlib.sha256(canonical.encode()).hexdigest()
        try:
            with db.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO decision_log
                        (log_id, agent_id, action_type, input_summary, output_summary,
                         confidence_score, risk_level, human_approved, timestamp,
                         chain_hash, prev_hash)
                    VALUES (%s::uuid, 'governance', 'decision', %s, %s,
                            1.0, 'low', TRUE, %s, %s, %s)
                    """,
                    (entry_id, summary[:255], summary, now, chain_hash, prev_hash),
                )
            db.commit()
        except psycopg2.DatabaseError as e:
            db.rollback()
            raise GovernanceError(f"Database error writing audit entry: {e}")
        return entry_id
    except GovernanceError:
        raise
    except Exception as e:
        db.rollback()
        raise GovernanceError(f"Unexpected error in _write_audit_entry: {e}")
