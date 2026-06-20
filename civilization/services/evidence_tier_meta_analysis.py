"""Evidence tier meta-analysis: empirical hierarchy updates (Phase 7)."""
from __future__ import annotations

import logging
import numpy as np

logger = logging.getLogger(__name__)


class EvidenceTierAnalyzer:
    """Analyze and update evidence hierarchy empirically."""

    def __init__(self):
        self.tier_failures: dict[str, dict[str, list[bool]]] = {}  # tier -> {domain -> [outcomes]}

    def tier_failure_rate(self, tier: str, domain: str, lookback_days: int = 365) -> float:
        """Compute failure rate for tier in domain."""
        if tier not in self.tier_failures or domain not in self.tier_failures[tier]:
            return 0.5  # Unknown

        outcomes = self.tier_failures[tier][domain]
        if not outcomes:
            return 0.5

        failures = sum(1 for o in outcomes if not o)
        return failures / len(outcomes)

    def update_tier_hierarchy(self, domain: str) -> dict:
        """Update tier order based on empirical failure rates."""
        tiers = ["formal_proof", "peer_reviewed", "textbook", "blog", "forum"]
        failure_rates = {t: self.tier_failure_rate(t, domain) for t in tiers}

        # Sort by failure rate (lower is better)
        sorted_tiers = sorted(tiers, key=lambda t: failure_rates[t])

        return {
            "tier_order": sorted_tiers,
            "failure_rates": failure_rates,
            "rationale": "Empirically updated hierarchy",
        }

    def record_outcome(self, tier: str, domain: str, outcome: bool) -> None:
        """Record outcome for tier/domain."""
        if tier not in self.tier_failures:
            self.tier_failures[tier] = {}
        if domain not in self.tier_failures[tier]:
            self.tier_failures[tier][domain] = []

        self.tier_failures[tier][domain].append(outcome)
