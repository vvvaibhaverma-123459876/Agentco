"""Learning curves: marginal cost analysis (Phase 8)."""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


class LearningCurveTracker:
    """Track and predict marginal costs."""

    BASE_COSTS = {
        "replication": 10.0,
        "re_analysis": 6.0,
        "mechanism_check": 5.0,
        "general": 8.0,
    }

    def marginal_cost(self, verification_type: str, nth_instance: int) -> float:
        """
        Compute marginal cost with learning curve.

        Cost = base_cost * (nth_instance ^ -0.3)  [power law]
        """
        base = self.BASE_COSTS.get(verification_type, 8.0)
        return base * math.pow(nth_instance, -0.3)

    def total_cost(self, verification_type: str, num_instances: int) -> float:
        """Total cost for N instances."""
        return sum(self.marginal_cost(verification_type, i) for i in range(1, num_instances + 1))
