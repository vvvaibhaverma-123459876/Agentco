"""Rotating gatekeepers prevent institutional capture (Phase 4)."""
from __future__ import annotations

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class RotatingGatekeeperPool:
    """Rotate reviewers to prevent capture."""

    def __init__(self, max_reviews_per_week: int = 10):
        self.max_reviews_per_week = max_reviews_per_week
        self.review_history: dict[str, list[str]] = defaultdict(list)  # agent_id -> [claim_ids]
        self.last_reviewer: dict[str, str] = {}  # stage -> last agent_id

    def assign_reviewer(self, stage: str, institution_id: str, eligible_reviewers: list[str]) -> str:
        """
        Assign reviewer, rotating to prevent capture.

        Args:
            stage: Review stage name
            institution_id: Institution
            eligible_reviewers: Pool of reviewers

        Returns:
            Assigned reviewer ID
        """
        if not eligible_reviewers:
            return "default_reviewer"

        # Avoid consecutive reuse
        last = self.last_reviewer.get(stage)
        available = [r for r in eligible_reviewers if r != last]

        if not available:
            available = eligible_reviewers

        # Prefer least loaded
        loads = {r: len(self.review_history[r]) for r in available}
        reviewer = min(available, key=lambda r: loads[r])

        self.last_reviewer[stage] = reviewer
        self.review_history[reviewer].append(f"{institution_id}_{stage}")

        return reviewer

    def get_reviewer_load(self, reviewer_id: str) -> int:
        """Get current load."""
        return len(self.review_history[reviewer_id])

    def is_overloaded(self, reviewer_id: str) -> bool:
        """Check if reviewer overloaded."""
        return self.get_reviewer_load(reviewer_id) > self.max_reviews_per_week
