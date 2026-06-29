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
from decimal import Decimal
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


def _as_float(value) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def propagate_institution(institution_id: str, ledger, db) -> dict:
    """
    Compute and persist department_score for each dept, then institution_score.
    Writes 'reputation_updated' memory events for changed scores.
    Returns {'institution_score': float|None, 'department_scores': {dept_id: score}}.

    Optimized: Batch-load all agents, use FOR UPDATE locks, cache ledger scores.
    """
    try:
        weights = _load_weights()
        now = datetime.now(timezone.utc)

        # Load institution + all departments in one transaction with locking
        try:
            with db.cursor() as cur:
                # Lock institution
                cur.execute(
                    "SELECT reputation_score FROM institutions WHERE id = %s FOR UPDATE",
                    (institution_id,),
                )
                inst_row = cur.fetchone()
                old_inst_score = _as_float(inst_row[0]) if inst_row else None

                # Load departments
                cur.execute(
                    "SELECT id, name, reputation_score FROM departments WHERE parent_id = %s AND status = 'active' FOR UPDATE",
                    (institution_id,),
                )
                depts = cur.fetchall()
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Database error loading institution/departments: {e}")

        # Batch-load all agents for all departments (single query instead of N queries)
        dept_agents: dict[str, list[str]] = {dept[0]: [] for dept in depts}
        try:
            with db.cursor() as cur:
                cur.execute(
                    """
                    SELECT department_id, agent_id
                    FROM agent_membership_edges
                    WHERE department_id = ANY(%s) AND active = TRUE
                    """,
                    ([dept[0] for dept in depts],),
                )
                for dept_id, agent_id in cur.fetchall():
                    dept_agents[dept_id].append(agent_id)
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Database error loading agents: {e}")

        # Cache agent scores (single ledger scan instead of per-agent)
        agent_scores: dict[str, tuple[Optional[float], int]] = {}
        all_agents = {agent_id for agents in dept_agents.values() for agent_id in agents}
        for agent_id in all_agents:
            agent_scores[agent_id] = _agent_score_and_count(agent_id, ledger)

        # Compute department scores (no N+1 queries)
        dept_scores: dict[str, Optional[float]] = {}
        for dept_id, dept_name, old_dept_score_raw in depts:
            old_dept_score = _as_float(old_dept_score_raw)
            members = dept_agents.get(dept_id, [])

            if not members:
                dept_scores[dept_id] = None
                continue

            total_w = 0.0
            weighted_sum = 0.0
            for agent_id in members:
                s, n = agent_scores.get(agent_id, (None, 0))
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

        # Compute institution score
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
    except RuntimeError:
        raise
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Unexpected error in propagate_institution: {e}")


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
    Retries once on failure.
    """
    try:
        delta = (new_score - old_score) if (new_score is not None and old_score is not None) else None
        mem_id = str(uuid.uuid4())

        # Use an explicit transaction so SET LOCAL survives to the UPDATE.
        old_autocommit = db.autocommit
        changed_autocommit = False
        if old_autocommit:
            db.autocommit = False
            changed_autocommit = True
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
        except Exception as e:
            db.rollback()
            raise RuntimeError(f"Database error persisting score update: {e}")
        finally:
            if changed_autocommit:
                db.autocommit = old_autocommit
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected error in _persist_score_update: {e}")
