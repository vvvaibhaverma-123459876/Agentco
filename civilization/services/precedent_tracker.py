"""Precedent compatibility tracking (Phase 6)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PrecedentAnalysis:
    """Precedent compatibility."""
    compatible_decisions: list[str]
    incompatible_decisions: list[str]
    coherence: float  # 0-1


class PrecedentTracker:
    """Track and assess precedent compatibility."""

    def __init__(self):
        self.norms: dict[str, str] = {}  # norm_id -> definition
        self.decisions: dict[str, dict] = {}  # decision_id -> {norm_id, outcome}

    def precedent_compatibility_score(self, new_norm: str, past_decisions: list[dict]) -> float:
        """
        Score compatibility with precedent.

        Args:
            new_norm: New norm text
            past_decisions: list of {norm, decision}

        Returns:
            Compatibility [0, 1]
        """
        if not past_decisions:
            return 1.0

        # Heuristic: count word overlap
        new_words = set(new_norm.lower().split())
        similarities = []

        for decision in past_decisions:
            past_norm = decision.get("norm", "")
            past_words = set(past_norm.lower().split())
            if past_words:
                overlap = len(new_words & past_words) / len(new_words | past_words)
                similarities.append(overlap)

        if not similarities:
            return 0.5

        avg_similarity = sum(similarities) / len(similarities)
        return avg_similarity

    def review_precedent_set(self, norm_id: str, all_decisions: list[dict]) -> PrecedentAnalysis:
        """
        Analyze precedent set for norm.

        Args:
            norm_id: Norm ID
            all_decisions: All past decisions

        Returns:
            PrecedentAnalysis
        """
        relevant_decisions = [d for d in all_decisions if d.get("norm_id") == norm_id]

        compatible = [d["decision_id"] for d in relevant_decisions if d.get("compatible", True)]
        incompatible = [d["decision_id"] for d in relevant_decisions if not d.get("compatible", True)]

        coherence = len(compatible) / len(relevant_decisions) if relevant_decisions else 0.5

        return PrecedentAnalysis(
            compatible_decisions=compatible,
            incompatible_decisions=incompatible,
            coherence=float(coherence),
        )
