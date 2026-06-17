"""
Epistemic Reserve — Deterministic Scoring Function (v1).

ALGORITHM SPECIFICATION (published; anyone may recompute from the public ledger):

    For each resolved, non-post-hoc prediction in a (agent × domain × horizon) cell:

        hardness(p)   = 2 * p * (1 - p)          # ∈ [0, 0.5]; 0 for trivial p≈0 or p≈1
        consequence_w = 2.0 if consequence else 1.0
        weight(p, c)  = hardness(p) * consequence_w

        log_score(p, o)   = log(p) if o else log(1-p)   # clipped to [ε, 1-ε]
        brier_score(p, o) = (p - o)²

        weighted_log   = weight * log_score(p, o)
        weighted_brier = weight * brier_score(p, o)

    Cell aggregate:
        total_weight       = Σ weight(pᵢ, cᵢ)
        cell_log_score     = Σ weighted_log_i   / total_weight   (or 0 if total_weight == 0)
        cell_brier_score   = Σ weighted_brier_i / total_weight
        cell_sharpness     = Σ (pᵢ * (1-pᵢ)) / n               # resolution of probability estimates

    Overall score (across all non-empty cells):
        overall_log_score  = Σ cell_log_score_i / n_cells

PROPERTIES:
  - PURE: given the same resolved predictions, any party recomputes identical scores.
  - No hidden weights, no operator overrides, no off-ledger inputs.
  - Trivial predictions (p ≈ 0 or 1) earn near-zero credit.
  - Post-hoc predictions are excluded.
  - Unresolved predictions are excluded.
  - Internal ground-truth sources are excluded (firewall, not scoring layer).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionRecord

EPSILON = 1e-9
CONSEQUENCE_WEIGHT_MULTIPLIER = 2.0


def hardness(probability: float) -> float:
    """Base-rate uncertainty: 2p(1-p) ∈ [0, 0.5]. Maximum at p=0.5."""
    return 2.0 * probability * (1.0 - probability)


def weight(probability: float, consequence: bool) -> float:
    """Calibration credit weight = hardness × consequence_multiplier."""
    cw = CONSEQUENCE_WEIGHT_MULTIPLIER if consequence else 1.0
    return hardness(probability) * cw


def log_score(probability: float, outcome: bool) -> float:
    """Proper log score, clipped to avoid ±∞."""
    p = max(min(probability, 1.0 - EPSILON), EPSILON)
    return math.log(p) if outcome else math.log(1.0 - p)


def brier_score(probability: float, outcome: bool) -> float:
    """Brier score: lower is better. Perfect = 0.0. Chance baseline = 0.25."""
    o = 1.0 if outcome else 0.0
    return (probability - o) ** 2


@dataclass(frozen=True)
class CellScore:
    """Aggregate score for one (agent × domain × horizon_class) cell."""
    agent_id: str
    domain: str
    horizon_class: str
    weighted_log_score: float    # Σ(weight × log_score) / Σweight; higher = better
    weighted_brier_score: float  # Σ(weight × brier) / Σweight; lower = better
    sharpness: float             # mean(p*(1-p)) — resolution of probability estimates
    sample_count: int            # number of resolved, non-post-hoc predictions in cell
    total_weight: float          # Σweight; near-0 means cell is essentially empty


@dataclass(frozen=True)
class ReserveScore:
    """
    Full scoring result for one agent across all (domain × horizon) cells.
    This is the input to ProofOfCalibration credential generation.
    """
    agent_id: str
    cells: list[CellScore]
    overall_log_score: float    # mean across non-empty cells
    overall_brier_score: float
    total_sample_count: int
    algorithm: str = "log_score+brier/hardness_weighted/v1"


def score_agent(
    records: list["PredictionRecord"],
    agent_id: str,
) -> ReserveScore:
    """
    Compute the full Reserve score for one agent from their resolved prediction records.

    Input: any iterable of PredictionRecord (can come from PredictionLedger.list_by_agent()).
    Only resolved, non-post-hoc records with boolean outcomes contribute.

    This function is PURE and DETERMINISTIC: same inputs → same outputs.
    Any party with access to the public ledger rows can call this and get identical results.
    """
    eligible = [
        r for r in records
        if r.resolved
        and not r.post_hoc
        and r.resolved_outcome is not None
    ]

    # Group by (domain, horizon_class)
    cells_map: dict[tuple[str, str], list["PredictionRecord"]] = {}
    for r in eligible:
        key = (r.domain, r.horizon_class)
        cells_map.setdefault(key, []).append(r)

    cell_scores: list[CellScore] = []
    for (domain, horizon_class), cell_records in sorted(cells_map.items()):
        total_w = 0.0
        sum_wlog = 0.0
        sum_wbrier = 0.0
        sum_sharpness = 0.0

        for r in cell_records:
            # consequence field may not exist on older records (pre-Reserve extension)
            consequence = getattr(r, "consequence", False) or False
            p = r.probability
            o = bool(r.resolved_outcome)

            w = weight(p, consequence)
            total_w += w
            sum_wlog += w * log_score(p, o)
            sum_wbrier += w * brier_score(p, o)
            sum_sharpness += p * (1.0 - p)

        n = len(cell_records)
        wlog = sum_wlog / total_w if total_w > 0 else 0.0
        wbrier = sum_wbrier / total_w if total_w > 0 else 0.0
        sharp = sum_sharpness / n if n > 0 else 0.0

        cell_scores.append(CellScore(
            agent_id=agent_id,
            domain=domain,
            horizon_class=horizon_class,
            weighted_log_score=wlog,
            weighted_brier_score=wbrier,
            sharpness=sharp,
            sample_count=n,
            total_weight=total_w,
        ))

    non_empty = [c for c in cell_scores if c.sample_count > 0]
    if non_empty:
        overall_log = sum(c.weighted_log_score for c in non_empty) / len(non_empty)
        overall_brier = sum(c.weighted_brier_score for c in non_empty) / len(non_empty)
    else:
        overall_log = 0.0
        overall_brier = 0.0

    return ReserveScore(
        agent_id=agent_id,
        cells=cell_scores,
        overall_log_score=overall_log,
        overall_brier_score=overall_brier,
        total_sample_count=len(eligible),
    )
