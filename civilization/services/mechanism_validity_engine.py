"""Mechanism validity validation (Phase 7)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class MechanismValidityEngine:
    """Validate proposed mechanisms for claims."""

    def validate_mechanism(self, claim: str, proposed_mechanism: str) -> dict:
        """
        Validate mechanism.

        Returns:
            {valid, confidence}
        """
        if not proposed_mechanism or len(proposed_mechanism) < 10:
            # No mechanism → penalty
            confidence = 0.45
            valid = False
            rationale = "No mechanism proposed"
        elif self._is_plausible(proposed_mechanism):
            # Plausible mechanism → boost
            confidence = 0.7
            valid = True
            rationale = "Plausible mechanism proposed"
        else:
            # Implausible mechanism → penalty
            confidence = 0.2
            valid = False
            rationale = "Implausible mechanism"

        return {
            "valid": valid,
            "confidence": confidence,
            "rationale": rationale,
        }

    def _is_plausible(self, mechanism: str) -> bool:
        """Heuristic: check for causal language."""
        causal_words = ["cause", "effect", "result", "lead", "produce", "mechanism"]
        return any(word in mechanism.lower() for word in causal_words)
