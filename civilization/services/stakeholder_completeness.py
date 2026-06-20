"""Stakeholder representation assessment (Phase 6)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class StakeholderCompletenessGraph:
    """Assess stakeholder representation."""

    def __init__(self):
        self.affected_parties_map: dict[str, list[str]] = {}

    def affected_parties(self, decision_id: str) -> list[str]:
        """Get affected stakeholder groups."""
        return self.affected_parties_map.get(decision_id, [])

    def register_decision(self, decision_id: str, affected_groups: list[str]) -> None:
        """Register affected groups for decision."""
        self.affected_parties_map[decision_id] = affected_groups

    def representation_score(self, decision_id: str, represented_groups: list[str]) -> float:
        """
        Score representation (0-1).

        Args:
            decision_id: Decision ID
            represented_groups: Groups actually represented

        Returns:
            Score: fully_represented / total_affected
        """
        affected = self.affected_parties(decision_id)

        if not affected:
            return 1.0

        represented_count = sum(1 for g in affected if g in represented_groups)
        score = represented_count / len(affected)

        # Return 0 if any group completely absent
        if represented_count < len(affected):
            return max(0.0, score)

        return score
