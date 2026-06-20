"""Byzantine-robust aggregation (Phase 3)."""
from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)


class ByzantineAggregator:
    """Robust aggregation ignoring outliers."""

    def robust_mean(self, trust_values: list[float], k_outliers: int = 1) -> float:
        """
        Compute robust mean by trimming extremes.

        Removes k largest and k smallest values.
        """
        if len(trust_values) <= 2 * k_outliers:
            return float(np.mean(trust_values))

        sorted_vals = sorted(trust_values)
        trimmed = sorted_vals[k_outliers:-k_outliers]

        if not trimmed:
            return float(np.mean(trust_values))

        return float(np.mean(trimmed))

    def detect_adversarial_votes(self, trust_values: list[float], threshold: float = 3.0) -> list[int]:
        """
        Detect outliers via median + MAD (median absolute deviation).

        Returns indices of adversarial votes.
        """
        if len(trust_values) < 3:
            return []

        values = np.array(trust_values)
        median = float(np.median(values))
        mad = float(np.median(np.abs(values - median)))

        if mad == 0:
            return []

        outlier_indices = []
        for i, val in enumerate(values):
            z_score = abs(val - median) / mad if mad > 0 else 0
            if z_score > threshold:
                outlier_indices.append(i)

        return outlier_indices
