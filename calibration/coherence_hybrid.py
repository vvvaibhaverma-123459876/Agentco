"""Coherence + Grounding hybrid evaluation (Phase 2)."""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


class CoherenceHybridEvaluator:
    """Evaluate plausibility via coherence + grounding."""

    def __init__(self, db=None):
        self.db = db

    def coherence_score(self, claim_id: str, all_beliefs: dict[str, float]) -> float:
        """Coherence: how well does claim cohere with other beliefs?"""
        if not all_beliefs or claim_id not in all_beliefs:
            return 0.5

        target_degree = all_beliefs[claim_id]
        if target_degree < 0.3:
            return 0.0  # Negligible beliefs don't contribute

        coherence_sum = 0.0
        count = 0
        for other_id, other_degree in all_beliefs.items():
            if other_id == claim_id:
                continue
            if other_degree > 0.3:  # Only consider non-negligible
                # Simple: similar beliefs cohere
                similarity = 1.0 - abs(target_degree - other_degree)
                coherence_sum += similarity * other_degree
                count += 1

        if count == 0:
            return 0.5

        return coherence_sum / count

    def grounding_score(self, claim_id: str, justifications: list) -> float:
        """Grounding: external evidence support."""
        if not justifications:
            return 0.0

        evidential_strength = 0.0
        total = 0
        for j in justifications:
            if j.justification_type in ["evidential", "replication"]:
                evidential_strength += j.strength
            total += 1

        if total == 0:
            return 0.0

        return min(1.0, evidential_strength / total)

    def joint_plausibility(self, claim_id: str, all_beliefs: dict[str, float], justifications: list) -> float:
        """Joint plausibility: weighted combination."""
        coherence = self.coherence_score(claim_id, all_beliefs)
        grounding = self.grounding_score(claim_id, justifications)
        return 0.3 * coherence + 0.7 * grounding
