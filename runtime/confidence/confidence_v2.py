"""
V2 Confidence layer — wraps stated confidence through TrustController.

INVARIANT: No agent may use stated_confidence directly in a decision.
           All confidence values that drive decisions MUST pass through
           trusted_confidence(), which applies the agent's actual track record.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.trust.trust_controller import TrustController

logger = logging.getLogger(__name__)


@dataclass
class TrustedOutput:
    stated_confidence: float
    trusted_confidence: float
    domain: str
    claim_type: str
    horizon_class: str
    degraded: bool          # True when trusted < stated (track record is weak)
    n_samples: int          # how many resolved predictions backed this trust factor


class ConfidenceV2:
    """
    Mediates between an agent's stated confidence and its earned trust score.
    Agents call get_trusted() to obtain the confidence value that should govern decisions.
    """

    def __init__(self, trust_controller: Optional["TrustController"] = None):
        self._trust = trust_controller

    def get_trusted(
        self,
        agent_id: str,
        stated: float,
        domain: str = "general",
        claim_type: str = "general",
        horizon_class: str = "short",
    ) -> TrustedOutput:
        if self._trust is None:
            # No trust controller wired — fall back to stated, flag as degraded
            logger.warning("ConfidenceV2: no TrustController wired for agent=%s; using stated=%.3f", agent_id, stated)
            return TrustedOutput(
                stated_confidence=stated,
                trusted_confidence=stated * 0.5,   # conservative 50% discount when unverified
                domain=domain,
                claim_type=claim_type,
                horizon_class=horizon_class,
                degraded=True,
                n_samples=0,
            )

        trusted = self._trust.trusted_confidence(
            stated=stated,
            subject_id=agent_id,
            subject_type="agent",
            domain=domain,
            claim_type=claim_type,
            horizon_class=horizon_class,
        )
        n = self._trust.get_sample_count(agent_id, domain, claim_type, horizon_class)
        return TrustedOutput(
            stated_confidence=stated,
            trusted_confidence=trusted,
            domain=domain,
            claim_type=claim_type,
            horizon_class=horizon_class,
            degraded=trusted < stated,
            n_samples=n,
        )
