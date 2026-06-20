"""Outside view correction: account for systematic biases (Phase 7)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class OutsideViewCorrector:
    """Correct for publication bias, selection effects."""

    CORRECTION_FACTORS = {
        "math": 1.0,  # No correction
        "empirical": 0.7,  # Publication bias, multiple comparisons
        "social": 0.6,  # High bias
        "opinion": 0.5,  # Very biased
        "general": 0.75,
    }

    def correction_factor(self, domain: str) -> float:
        """Get outside view correction factor."""
        return self.CORRECTION_FACTORS.get(domain, 0.75)

    def apply_correction(self, evidence_strength: float, domain: str) -> float:
        """Apply correction to evidence strength."""
        factor = self.correction_factor(domain)
        return evidence_strength * factor
