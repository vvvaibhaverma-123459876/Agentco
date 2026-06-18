"""
Civilization layer — Reputation propagation service.

EXACT FORMULA (per spec):

  agent_score(a)      = Reserve credential overall_log_score for agent a
  department_score(d) = Σ_{a in d} w_a * agent_score(a) / Σ_{a in d} w_a
                        where w_a = agent_score sample_count
  institution_score(i)= Σ_{d in i} W_d * department_score(d) / Σ_{d in i} W_d
                        where W_d = department weights from reputation_weights.yaml

  Empty groups → score = NULL (not 0). NULLs excluded from parent aggregation.

Propagation runs in one transaction per institution and writes a 'reputation_updated'
memory event per entity whose score changed. It sets the session var
civilization.reputation_update_authorized = 'true' to satisfy the trigger guard.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from reserve.scoring.scoring_function import score_agent

_WEIGHTS_FILE = Path(__file__).resolve().parents[1] / "reputation_weights.yaml"


def _load_weights() -> dict[str, float]:
    with open(_WEIGHTS_FILE) as f:
        data = yaml.safe_load(f)
    return data.get("department_weights", {})


def _agent_score_and_count(agent_id: str, ledger) -> tuple[Optional[float], int]:
    """
    Compute agent_score(a) = Reserve credential overall_log_score from the ledger.
    Returns (score, sample_count). score is None if no resolved predictions.
    """
    records = ledger.list_by_agent(agent_id)
    reserve_score = score_agent(records, agent_id)
    if reserve_score.total_sample_count == 0:
        return None, 0
    return reserve_score.overall_log_score, reserve_score.total_sample_count


def propagate_institution(institution_id: str, ledger, db) -> dict:
    """
    Compute and persist department_score for each dept, then institution_score.
    Writes 'reputation_updated' memory events for changed scores.
    Returns {'institution_score': float|None, 'department_scores': {dept_id: score}}.

    Uses a single psycopg2 connection for both SELECT and the guarded UPDATE.
    """
    weights = _load_weights()
    now = datetime.now(timezone.utc)

    # Load departments
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, name, reputation_score FROM departments WHERE parent_id = %s AND status = 'active'",
            (institution_id,),
        )
        depts = cur.fetchall()  # (dept_id, dept_name, old_score)

    dept_scores: dict[str, Optional[float]] = {}

    # ── Phase A: compute department scores ──────────────────────────────────
    for dept_id, dept_name, old_dept_score in depts:
        with db.cursor() as cur:
            cur.execute(
                "SELECT agent_id FROM agent_membership_edges "
                "WHERE department_id = %s AND active = TRUE",
                (dept_id,),
            )
            members = [r[0] for r in cur.fetchall()]

        if not members:
            dept_scores[dept_id] = None
            continue

        total_w = 0.0
        weighted_sum = 0.0
        for agent_id in members:
            s, n = _agent_score_and_count(agent_id, ledger)
            if s is None:
                continue
            w = float(n)
            total_w += w
            weighted_sum += w * s

        new_dept_score = (weighted_sum / total_w) if total_w > 0 else None
        dept_scores[dept_id] = new_dept_score

        if new_dept_score != old_dept_score:
            _persist_score_update(
                entity_table="departments",
                entity_id=dept_id,
                entity_type="department",
                new_score=new_dept_score,
                old_score=old_dept_score,
                now=now,
                db=db,
            )

    # ── Phase B: compute institution score ──────────────────────────────────
    with db.cursor() as cur:
        cur.execute(
            "SELECT reputation_score FROM institutions WHERE id = %s",
            (institution_id,),
        )
        row = cur.fetchone()
    old_inst_score = row[0] if row else None

    dept_weight_sum = 0.0
    dept_weighted_sum = 0.0
    for dept_id, dept_name, _ in depts:
        s = dept_scores.get(dept_id)
        if s is None:
            continue
        W = weights.get(dept_name, 1.0)
        dept_weight_sum += W
        dept_weighted_sum += W * s

    new_inst_score = (dept_weighted_sum / dept_weight_sum) if dept_weight_sum > 0 else None

    if new_inst_score != old_inst_score:
        _persist_score_update(
            entity_table="institutions",
            entity_id=institution_id,
            entity_type="institution",
            new_score=new_inst_score,
            old_score=old_inst_score,
            now=now,
            db=db,
        )

    return {"institution_score": new_inst_score, "department_scores": dept_scores}


def _persist_score_update(
    entity_table: str,
    entity_id: str,
    entity_type: str,
    new_score: Optional[float],
    old_score: Optional[float],
    now: datetime,
    db,
) -> None:
    """
    Write the memory event FIRST, then set the session flag, then UPDATE.
    The trigger checks the flag; without it the UPDATE raises.
    """
    delta = (new_score - old_score) if (new_score is not None and old_score is not None) else None
    mem_id = str(uuid.uuid4())

    # Use an explicit transaction so SET LOCAL survives to the UPDATE.
    old_autocommit = db.autocommit
    db.autocommit = False
    try:
        with db.cursor() as cur:
            # 1. Write memory event
            cur.execute(
                """
                INSERT INTO civilization_memory_events
                    (id, entity_type, entity_id, event_type, summary,
                     evidence_refs, reputation_delta, created_at)
                VALUES (%s, %s, %s, 'reputation_updated', %s, '{}'::jsonb, %s, %s)
                """,
                (
                    mem_id, entity_type, entity_id,
                    f"{entity_type} {entity_id} reputation updated to {new_score}",
                    delta, now,
                ),
            )
            # 2. Authorize the score UPDATE within this transaction
            cur.execute("SET LOCAL civilization.reputation_update_authorized = 'true'")
            # 3. Update the score — trigger checks the session var
            cur.execute(
                f"UPDATE {entity_table} SET reputation_score = %s, updated_at = %s WHERE id = %s",
                (new_score, now, entity_id),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.autocommit = old_autocommit
