"""Temporal decay of evidence (Phase 7)."""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


class TemporalDecayEngine:
    """Apply temporal decay to evidence based on age."""

    HALF_LIVES = {
        "math": math.inf,  # No decay for math
        "tech_benchmark": 90,  # 90 days half-life
        "biology": 365,  # 1 year half-life
        "social": 180,  # 6 months
        "general": 180,
    }

    def decay_weight(self, evidence_age_days: int, domain: str) -> float:
        """Compute decay weight: exp(-days / λ)."""
        lambda_half = self.HALF_LIVES.get(domain, 180)

        if lambda_half == math.inf:
            return 1.0

        return math.exp(-evidence_age_days / lambda_half)

    def get_half_life(self, domain: str) -> float:
        """Get half-life in days."""
        return self.HALF_LIVES.get(domain, 180)
