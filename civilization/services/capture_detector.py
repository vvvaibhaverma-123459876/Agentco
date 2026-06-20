"""Institutional capture detection (Phase 5)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CaptureDetector:
    """Detect signs of institutional capture."""

    def capture_likelihood_score(self, institution_id: str, metrics: dict) -> float:
        """
        Compute capture likelihood (0-1).

        Args:
            institution_id: Institution ID
            metrics: {domain_concentration, dissent_rate_change, review_time_avg_seconds, self_citation_rate}

        Returns:
            Capture score [0, 1]
        """
        score = 0.0

        # Domain authority concentration: one agent > 0.5 total expertise
        concentration = metrics.get("domain_concentration", 0.0)
        if concentration > 0.5:
            score += 0.3

        # Dissent disappearance: dissent rate drops significantly
        dissent_change = metrics.get("dissent_rate_change", 0.0)
        if dissent_change < -0.2:  # Major drop
            score += 0.3

        # Rubber-stamp approval: avg review time < 5 min (300 seconds)
        review_time = metrics.get("review_time_avg_seconds", 300)
        if review_time < 300:
            score += 0.2

        # Self-citation dominance: > 0.7 self-citations
        self_citation = metrics.get("self_citation_rate", 0.0)
        if self_citation > 0.7:
            score += 0.2

        return min(1.0, score)
