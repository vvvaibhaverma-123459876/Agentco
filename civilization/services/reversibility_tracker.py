"""Reversibility assessment (Phase 6)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ReversibilityTracker:
    """Track reversibility of decisions."""

    def rate_reversibility(self, decision_id: str, metrics: dict) -> str:
        """
        Rate reversibility.

        Args:
            decision_id: Decision ID
            metrics: {resource_cost, time_to_undo, irreversible_harm}

        Returns:
            'fully_reversible', 'partially_reversible', 'irreversible'
        """
        resource_cost = metrics.get("resource_cost", 0)
        time_to_undo = metrics.get("time_to_undo_days", 1000)
        irreversible_harm = metrics.get("irreversible_harm", False)

        if irreversible_harm:
            return "irreversible"

        if resource_cost < 1000 and time_to_undo < 30:
            return "fully_reversible"

        if resource_cost < 10000 and time_to_undo < 365:
            return "partially_reversible"

        return "irreversible"

    def repair_cost(self, decision_id: str, metrics: dict) -> float:
        """Estimate cost to undo."""
        return float(metrics.get("resource_cost", 1000))

    def deliberation_bar(self, reversibility: str, irreversible_harm: bool) -> int:
        """
        Deliberation stages required.

        Args:
            reversibility: fully/partially/irreversible
            irreversible_harm: Whether decision causes irreversible harm

        Returns:
            Number of review stages (1-5+)
        """
        if irreversible_harm:
            return 5

        if reversibility == "irreversible":
            return 4

        if reversibility == "partially_reversible":
            return 2

        return 1
