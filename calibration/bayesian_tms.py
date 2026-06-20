"""
Probabilistic Bayesian Truth Maintenance System (Phase 2).

Replaces binary IN/OUT with belief degrees ∈ [0,1].
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import math

logger = logging.getLogger(__name__)

PRIOR_DEGREE = 0.5
BASE_RATE_FALSE = 0.4


@dataclass
class Justification:
    """Support for a belief."""
    justification_id: str
    claim_id: str
    supporting_claim_ids: list[str] = field(default_factory=list)
    strength: float = 0.7  # ∈ [0, 1]
    justification_type: str = "evidential"  # evidential, deductive, replication, institutional, default
    is_conditional: bool = False
    condition: Optional[str] = None

    def is_valid(self, belief_degrees: dict[str, float]) -> bool:
        """Check if justification is valid (conditions met)."""
        if not self.is_conditional or self.condition is None:
            return True
        return belief_degrees.get(self.condition, 0.5) > 0.7


@dataclass
class ProbabilisticBeliefNode:
    """Belief node with degree of belief ∈ [0, 1]."""
    claim_id: str
    degree_of_belief: float = PRIOR_DEGREE
    justifications: list[Justification] = field(default_factory=list)
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[tuple[datetime, float]] = field(default_factory=list)

    def update_from_justifications(self, belief_degrees: dict[str, float]) -> float:
        """
        Update belief using Bayesian update.

        P(claim | justifications) via Bayes rule:
        Prior odds = P / (1 - P) where P = PRIOR_DEGREE
        Likelihood ratio = ∏(strength / (1 - strength))
        Posterior odds = prior_odds × likelihood_ratio
        Posterior = posterior_odds / (1 + posterior_odds)
        """
        # Filter valid justifications
        valid_justifications = [
            j for j in self.justifications if j.is_valid(belief_degrees)
        ]

        if not valid_justifications:
            # No valid justifications, revert to prior
            self.degree_of_belief = PRIOR_DEGREE
            return PRIOR_DEGREE

        # Compute prior odds
        prior = PRIOR_DEGREE
        prior_odds = prior / (1 - prior) if prior < 1 else 1e6

        # Compute likelihood ratio from justifications
        likelihood_ratio = 1.0
        for j in valid_justifications:
            if j.strength > 0 and j.strength < 1:
                strength = j.strength
                lr = strength / (1 - strength)
                likelihood_ratio *= lr

        # Compute posterior odds
        posterior_odds = prior_odds * likelihood_ratio

        # Convert back to probability
        posterior = posterior_odds / (1 + posterior_odds)
        posterior = max(0.0, min(1.0, posterior))

        self.degree_of_belief = posterior
        self.last_updated = datetime.now(timezone.utc)
        self.history.append((self.last_updated, posterior))

        logger.debug(
            "BELIEF UPDATE: claim=%s prior=%.3f posterior=%.3f valid_justifications=%d",
            self.claim_id, prior, posterior, len(valid_justifications)
        )

        return posterior

    def sensitivity_analysis(self, justification_id: str, belief_degrees: dict[str, float]) -> float:
        """
        Compute ΔP when justification is removed.

        Returns: change in degree of belief
        """
        # Save current state
        original_degree = self.degree_of_belief

        # Remove justification temporarily
        target_just = None
        for j in self.justifications:
            if j.justification_id == justification_id:
                target_just = j
                break

        if target_just is None:
            return 0.0

        self.justifications.remove(target_just)

        # Recompute without it
        new_degree = self.update_from_justifications(belief_degrees)

        # Restore
        self.justifications.append(target_just)
        self.degree_of_belief = original_degree

        return abs(new_degree - original_degree)

    def add_justification(self, justification: Justification) -> None:
        """Add a justification."""
        self.justifications.append(justification)

    def get_state(self) -> dict:
        """Return current state."""
        return {
            "claim_id": self.claim_id,
            "degree_of_belief": self.degree_of_belief,
            "n_justifications": len(self.justifications),
            "n_valid": sum(1 for j in self.justifications),
            "last_updated": self.last_updated,
            "history_length": len(self.history),
        }
