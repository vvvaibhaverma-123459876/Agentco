"""Attention economics: reviewer load balancing (Phase 8)."""
from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class AttentionEconomicsEngine:
    """Balance reviewer workload, prevent burnout."""

    def __init__(self, max_per_week: int = 10):
        self.max_per_week = max_per_week
        self.reviewer_reviews: dict[str, list[str]] = defaultdict(list)

    def load_balance_reviewers(self, all_reviews_needed: list[str]) -> dict:
        """Distribute reviews evenly."""
        reviewers = list(set(r for r in self.reviewer_reviews.keys()) or ["reviewer_1", "reviewer_2"])

        allocation = defaultdict(list)
        for i, review in enumerate(all_reviews_needed):
            assigned = reviewers[i % len(reviewers)]
            allocation[assigned].append(review)
            self.reviewer_reviews[assigned].append(review)

        load_scores = {r: len(self.reviewer_reviews[r]) for r in reviewers}

        return {
            "allocation": dict(allocation),
            "load_score": load_scores,
            "balanced": max(load_scores.values()) - min(load_scores.values()) <= 1,
        }

    def burnout_risk(self, reviewer_id: str) -> float:
        """Assess burnout risk [0, 1]."""
        load = len(self.reviewer_reviews.get(reviewer_id, []))
        risk = min(1.0, load / self.max_per_week)
        return risk

    def is_overloaded(self, reviewer_id: str) -> bool:
        """Check if overloaded."""
        return self.burnout_risk(reviewer_id) > 0.9
