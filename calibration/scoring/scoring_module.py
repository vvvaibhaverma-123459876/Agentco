"""
Scoring Module — Brier score, log score, ECE, reliability diagrams.

Used by the Resolution Service and the Trust Controller.
All scores are computed relative to the stated probability at prediction time
(not any post-hoc adjusted value).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from calibration.ledger.prediction_ledger import PredictionRecord


@dataclass
class CalibrationReport:
    agent_id: str
    domain: str
    sample_count: int
    mean_brier: float
    mean_log: float
    ece: float                          # Expected Calibration Error
    reliability_bins: list[dict]        # [{bin_centre, mean_stated, mean_actual, count}]
    overconfidence: float               # positive = overconfident
    underconfidence: float              # positive = underconfident
    horizon_breakdown: dict[str, float] # {horizon_class: mean_brier}


class ScoringModule:

    N_BINS = 10  # for ECE / reliability diagram

    def brier_score(self, probability: float, outcome: bool) -> float:
        """Lower is better. Perfect = 0.0. Chance baseline = 0.25."""
        o = 1.0 if outcome else 0.0
        return (probability - o) ** 2

    def log_score(self, probability: float, outcome: bool, epsilon: float = 1e-9) -> float:
        """Higher is better (less negative). Log-loss variant."""
        p = max(min(probability, 1 - epsilon), epsilon)
        return math.log(p) if outcome else math.log(1 - p)

    def calibration_report(
        self,
        records: list["PredictionRecord"],
        agent_id: str,
        domain: str = "all",
    ) -> CalibrationReport:
        resolved = [r for r in records if r.resolved and not r.post_hoc and r.resolved_outcome is not None]
        n = len(resolved)
        if n == 0:
            return CalibrationReport(
                agent_id=agent_id, domain=domain, sample_count=0,
                mean_brier=0.0, mean_log=0.0, ece=0.0,
                reliability_bins=[], overconfidence=0.0, underconfidence=0.0,
                horizon_breakdown={},
            )

        mean_brier = sum(r.brier_score or 0.0 for r in resolved) / n
        mean_log = sum(r.log_score or 0.0 for r in resolved) / n

        ece, bins = self._compute_ece(resolved)
        over, under = self._compute_over_under_confidence(bins)

        horizon_breakdown: dict[str, float] = {}
        for h in ("short", "medium", "long"):
            h_records = [r for r in resolved if r.horizon_class == h]
            if h_records:
                horizon_breakdown[h] = sum(r.brier_score or 0.0 for r in h_records) / len(h_records)

        return CalibrationReport(
            agent_id=agent_id, domain=domain, sample_count=n,
            mean_brier=mean_brier, mean_log=mean_log, ece=ece,
            reliability_bins=bins, overconfidence=over, underconfidence=under,
            horizon_breakdown=horizon_breakdown,
        )

    def _compute_ece(self, records: list["PredictionRecord"]) -> tuple[float, list[dict]]:
        """Compute Expected Calibration Error using equal-width bins."""
        bins: list[dict] = []
        bin_width = 1.0 / self.N_BINS

        for i in range(self.N_BINS):
            low = i * bin_width
            high = (i + 1) * bin_width
            bin_centre = (low + high) / 2

            in_bin = [r for r in records if low <= r.probability < high]
            if not in_bin:
                continue

            mean_stated = sum(r.probability for r in in_bin) / len(in_bin)
            mean_actual = sum(1.0 if r.resolved_outcome else 0.0 for r in in_bin) / len(in_bin)
            bins.append({
                "bin_centre": bin_centre,
                "mean_stated": mean_stated,
                "mean_actual": mean_actual,
                "count": len(in_bin),
            })

        n = len(records)
        ece = sum(b["count"] / n * abs(b["mean_stated"] - b["mean_actual"]) for b in bins)
        return ece, bins

    def _compute_over_under_confidence(self, bins: list[dict]) -> tuple[float, float]:
        over = sum(max(0, b["mean_stated"] - b["mean_actual"]) * b["count"] for b in bins)
        under = sum(max(0, b["mean_actual"] - b["mean_stated"]) * b["count"] for b in bins)
        total = sum(b["count"] for b in bins) or 1
        return over / total, under / total
