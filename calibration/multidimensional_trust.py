"""4D trust profiles: competence, reliability, integrity, benevolence (Phase 3)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MultidimensionalTrust:
    """4-dimensional trust profile."""
    competence: float = 0.5  # Knows domain
    reliability: float = 0.5  # Consistent
    integrity: float = 0.5  # Not self-serving
    benevolence: float = 0.5  # Cares about outcomes

    def __post_init__(self):
        """Clip to [0, 1]."""
        self.competence = max(0.0, min(1.0, self.competence))
        self.reliability = max(0.0, min(1.0, self.reliability))
        self.integrity = max(0.0, min(1.0, self.integrity))
        self.benevolence = max(0.0, min(1.0, self.benevolence))

    def overall_trust(self, context: str = "general") -> float:
        """
        Compute weighted overall trust by context.

        Contexts:
        - technical: comp=0.6, rel=0.25, int=0.1, ben=0.05
        - ethical: comp=0.1, rel=0.2, int=0.4, ben=0.3
        - financial: comp=0.2, rel=0.6, int=0.15, ben=0.05
        - general: comp=0.4, rel=0.3, int=0.2, ben=0.1
        """
        weights = {
            "technical": {"comp": 0.6, "rel": 0.25, "int": 0.1, "ben": 0.05},
            "ethical": {"comp": 0.1, "rel": 0.2, "int": 0.4, "ben": 0.3},
            "financial": {"comp": 0.2, "rel": 0.6, "int": 0.15, "ben": 0.05},
            "general": {"comp": 0.4, "rel": 0.3, "int": 0.2, "ben": 0.1},
        }

        w = weights.get(context, weights["general"])

        trust = (
            w["comp"] * self.competence +
            w["rel"] * self.reliability +
            w["int"] * self.integrity +
            w["ben"] * self.benevolence
        )

        return max(0.0, min(1.0, trust))

    def get_profile(self) -> dict:
        """Return profile as dict."""
        return {
            "competence": self.competence,
            "reliability": self.reliability,
            "integrity": self.integrity,
            "benevolence": self.benevolence,
        }
