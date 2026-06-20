"""Domain-specific priors (Phase 7)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class DomainSpecificPriors:
    """Domain-specific belief priors."""

    PRIORS = {
        "math": 0.95,  # proof > anything
        "empirical": 0.8,  # experiment > theory
        "social": 0.7,  # meta-analysis > anecdote
        "philosophy": 0.5,  # reasoned argument
        "opinion": 0.3,  # subjective
    }

    def prior(self, domain: str) -> float:
        """Get prior for domain."""
        return self.PRIORS.get(domain, 0.5)

    def justification_for_prior(self, domain: str) -> str:
        """Explain prior choice."""
        explanations = {
            "math": "Mathematical proofs are deductive",
            "empirical": "Experiments > theory in empirical domains",
            "social": "Meta-analysis aggregates multiple studies",
            "philosophy": "Reasoned argument is primary tool",
            "opinion": "Subjective views have low credibility",
        }
        return explanations.get(domain, "Domain prior 0.5 (neutral)")
