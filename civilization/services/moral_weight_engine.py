"""Moral weight assignment (Phase 6)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MoralWeightAssignment:
    """Moral weight assignment."""
    entity: str
    weight: float  # 0-1, reflects moral consideration
    justification: str
    revisable: bool


class MoralWeightEngine:
    """Assign and track moral weights."""

    def __init__(self):
        self.weights: dict[str, float] = {}
        self.weight_dependencies: dict[str, list[str]] = {}  # weight_id -> [decision_ids]

    def assign_moral_weight(self, entity_or_group: str, context: str) -> MoralWeightAssignment:
        """
        Assign moral weight to entity.

        Args:
            entity_or_group: Entity identifier
            context: Context (e.g., 'human', 'animal', 'ecosystem')

        Returns:
            MoralWeightAssignment
        """
        # Simplified: context-based defaults
        weight_map = {
            "human": 1.0,
            "sentient_animal": 0.5,
            "non_sentient_animal": 0.1,
            "ecosystem": 0.3,
            "institution": 0.2,
        }

        weight = weight_map.get(context, 0.5)
        self.weights[entity_or_group] = weight

        return MoralWeightAssignment(
            entity=entity_or_group,
            weight=weight,
            justification=f"Assigned based on context: {context}",
            revisable=True,
        )

    def track_weight_dependencies(self, decision_id: str, affected_entities: list[str]) -> dict:
        """
        Track decisions dependent on moral weights.

        Args:
            decision_id: Decision ID
            affected_entities: Entities affected

        Returns:
            Dependency info
        """
        dependent_decisions = []
        for entity in affected_entities:
            if entity in self.weight_dependencies:
                dependent_decisions.extend(self.weight_dependencies[entity])

        return {
            "decision_id": decision_id,
            "dependent_decisions": dependent_decisions,
            "weight_change_impact": {entity: self.weights.get(entity, 0.5) for entity in affected_entities},
        }
