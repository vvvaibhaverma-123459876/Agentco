"""
Epistemic Reserve — Weighted Decision Engine (Phase 2).

Aggregates stakes by credential weight to resolve a belief question.
Voting weight = max(0, cell_log_score) at stake time (from the staker's
Proof-of-Calibration credential). Decision = weighted majority.

This is a deterministic, pure function given the list of stakes.
The same stakes always produce the same decision — independently recomputable.
"""
from __future__ import annotations

from dataclasses import dataclass

from reserve.staking.staking import StakeRecord


@dataclass(frozen=True)
class WeightedDecision:
    question_id: str
    total_weight: float
    weight_for_true: float
    weight_for_false: float
    weighted_outcome: bool       # True if weight_for_true > weight_for_false
    is_tie: bool                 # True if weights are exactly equal (outcome defaults False)
    stake_count: int
    effective_stake_count: int   # stakes with weight > 0 (Sybil-filtered)
    sybil_filtered_count: int    # stakes with weight == 0 (zero-weight identities)

    # COLLUSION-RESISTANCE PROPERTY proof values (for audit):
    max_single_weight: float     # highest weight any one agent contributed
    weight_concentration: float  # max_single_weight / total_weight (Herfindahl-like)


def resolve_question(
    question_id: str,
    stakes: list[StakeRecord],
) -> WeightedDecision:
    """
    Compute the weighted decision for a question from its stakes.

    This function is PURE and DETERMINISTIC: same stakes → same decision.
    The outcome is the weighted majority position. Ties default to False.

    Sybil-filtered_count reports how many zero-weight stakes were silently
    discarded — these are agents without real reality-contact in the
    (domain × horizon) cell, demonstrating the collusion-resistance property.
    """
    if not stakes:
        return WeightedDecision(
            question_id=question_id,
            total_weight=0.0,
            weight_for_true=0.0,
            weight_for_false=0.0,
            weighted_outcome=False,
            is_tie=True,
            stake_count=0,
            effective_stake_count=0,
            sybil_filtered_count=0,
            max_single_weight=0.0,
            weight_concentration=0.0,
        )

    weight_for_true = sum(s.stake_weight for s in stakes if s.position)
    weight_for_false = sum(s.stake_weight for s in stakes if not s.position)
    total_weight = weight_for_true + weight_for_false
    is_tie = weight_for_true == weight_for_false
    weighted_outcome = weight_for_true > weight_for_false

    effective = [s for s in stakes if s.stake_weight > 0.0]
    sybil_filtered = [s for s in stakes if s.stake_weight == 0.0]
    max_w = max((s.stake_weight for s in stakes), default=0.0)
    concentration = max_w / total_weight if total_weight > 0 else 0.0

    return WeightedDecision(
        question_id=question_id,
        total_weight=total_weight,
        weight_for_true=weight_for_true,
        weight_for_false=weight_for_false,
        weighted_outcome=weighted_outcome,
        is_tie=is_tie,
        stake_count=len(stakes),
        effective_stake_count=len(effective),
        sybil_filtered_count=len(sybil_filtered),
        max_single_weight=max_w,
        weight_concentration=concentration,
    )


def persist_decision(decision: WeightedDecision, db) -> None:
    """Write the weighted aggregation result back to belief_questions."""
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE belief_questions
               SET resolved = TRUE,
                   resolved_at = NOW(),
                   total_weight = %s,
                   weight_for_true = %s,
                   weight_for_false = %s,
                   weighted_outcome = %s
             WHERE question_id = %s
            """,
            (
                decision.total_weight,
                decision.weight_for_true,
                decision.weight_for_false,
                decision.weighted_outcome,
                decision.question_id,
            ),
        )
    if callable(getattr(db, "commit", None)):
        db.commit()
