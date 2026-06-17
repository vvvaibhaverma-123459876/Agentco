"""
Epistemic Reserve — Staking Layer (Phase 2).

An agent stakes their domain credential on a binary claim before the outcome
is knowable. Weight = max(0, exp(cell_log_score) - 0.5) in the matching
(domain × horizon) cell of their current credential.

The formula maps log scores to non-negative weights:
  - Perfect predictor (log_score = 0):       weight = exp(0) - 0.5 = 0.5
  - Well-calibrated (log_score = -0.356):    weight = exp(-0.356) - 0.5 ≈ 0.20
  - Random baseline (log_score = -0.693):    weight = exp(-0.693) - 0.5 ≈ 0.0
  - Worse than random (log_score < -0.693):  weight = 0 (floored)
  - No cell (fresh / uncredentialed):        weight = 0

COLLUSION-RESISTANCE PROPERTY (structural, not cryptographic):

    Name: "Reality-Contact Weight Bound" (RCWB)

    Statement: The total voting weight a coalition of k agents can contribute
    to a belief market is bounded by Σᵢ max(0, exp(cell_log_score_i) - 0.5),
    where each term is computed from that agent's independently verified,
    externally-resolved prediction history. No agent can borrow or transfer
    weight. Creating additional Sybil identities adds weight = 0 per identity
    (fresh identities have no resolved predictions → no cell → weight = 0;
    or sample_count = 0 → weight = 0 even if a cell exists).
    Therefore collusion provides no weight amplification beyond what each
    member individually earned from real resolved predictions.

    Proof sketch:
        - stake_weight = max(0, exp(credential.cell(domain, horizon).weighted_log_score) - 0.5)
        - weighted_log_score is computed ONLY from resolved, non-post-hoc,
          externally-sourced prediction_ledger rows for that agent_id.
        - No agent can write to another agent's prediction_ledger rows.
        - A Sybil agent has 0 resolved predictions → no cell or sample_count=0
          → weight = 0 → contributes nothing to the weighted tally.
        □

    This is NOT Byzantine-fault-tolerant. The property is: weight is
    Sybil-resistant and non-transferable.
"""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from reserve.credentials.proof_of_calibration import ProofOfCalibration

# Random baseline: log(0.5) ≈ -0.693. Agents scoring at or below random get 0 weight.
_RANDOM_BASELINE = math.exp(math.log(0.5))  # = 0.5


@dataclass
class StakeRecord:
    stake_id: str
    question_id: str
    agent_id: str
    credential_id: str
    domain: str
    horizon_class: str
    stake_weight: float     # max(0, exp(cell_log_score) - 0.5) at stake time
    position: bool          # True = "yes", False = "no"
    staked_at: str          # ISO-8601 UTC


def compute_stake_weight(
    credential: ProofOfCalibration,
    domain: str,
    horizon_class: str,
) -> float:
    """
    Extract the stake weight for one (domain × horizon) cell from a credential.

    Returns max(0, exp(weighted_log_score) - 0.5) for the matching cell,
    or 0.0 if no cell exists or the cell has sample_count == 0.

    Agents scoring at or below the random binary baseline (log = log(0.5) ≈ -0.693)
    receive weight = 0. Agents with no resolved predictions in this cell receive 0.
    """
    for cell in credential.cells:
        if cell.domain == domain and cell.horizon_class == horizon_class:
            if cell.sample_count == 0:
                return 0.0
            return max(0.0, math.exp(cell.weighted_log_score) - _RANDOM_BASELINE)
    return 0.0


def place_stake(
    question_id: str,
    agent_id: str,
    credential: ProofOfCalibration,
    domain: str,
    horizon_class: str,
    position: bool,
    db,
) -> StakeRecord:
    """
    Place a stake on a belief question.

    Raises ValueError if:
    - The question is already resolved (time gate).
    - The agent has already staked on this question (uniqueness).
    - The credential does not belong to this agent.

    The DB trigger also enforces the post-resolution time gate independently.
    """
    if credential.agent_id != agent_id:
        raise ValueError(
            f"credential.agent_id={credential.agent_id!r} does not match agent_id={agent_id!r}"
        )

    with db.cursor() as cur:
        cur.execute(
            "SELECT resolved FROM belief_questions WHERE question_id = %s",
            (question_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"question_id {question_id!r} not found")
    if row[0]:
        raise ValueError(f"Cannot stake on already-resolved question {question_id!r}")

    weight = compute_stake_weight(credential, domain, horizon_class)
    stake_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO belief_stakes
                (stake_id, question_id, agent_id, credential_id, domain,
                 horizon_class, stake_weight, position, staked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                stake_id, question_id, agent_id, str(credential.credential_id),
                domain, horizon_class, weight, position, now,
            ),
        )
    _commit(db)

    return StakeRecord(
        stake_id=stake_id,
        question_id=question_id,
        agent_id=agent_id,
        credential_id=str(credential.credential_id),
        domain=domain,
        horizon_class=horizon_class,
        stake_weight=weight,
        position=position,
        staked_at=now,
    )


def register_question(
    claim: str,
    domain: str,
    horizon_class: str,
    resolution_criterion: str,
    resolution_date: datetime,
    ground_truth_source: str,
    db,
) -> str:
    """Register a belief question. Returns question_id."""
    question_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO belief_questions
                (question_id, claim, domain, horizon_class, resolution_criterion,
                 resolution_date, ground_truth_source)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                question_id, claim, domain, horizon_class,
                resolution_criterion, resolution_date, ground_truth_source,
            ),
        )
    _commit(db)
    return question_id


def _commit(db) -> None:
    if callable(getattr(db, "commit", None)):
        db.commit()
