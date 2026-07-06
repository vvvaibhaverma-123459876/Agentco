"""
Decay Tracker — knowledge has a half-life.

reality_validated beliefs decay over time without fresh reality contact.
Decay rate is belief-type-dependent. At trusted_until, a belief is reclassified
to provisional until it earns new reality contact.

This prevents old evidence from conferring eternal authority.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.firewall.firewall import Belief, RealitySimulationFirewall

logger = logging.getLogger(__name__)

# Default half-lives by domain/claim_type
DEFAULT_HALF_LIVES_DAYS: dict[str, int] = {
    "market_dynamics": 30,
    "competitive_landscape": 60,
    "customer_behaviour": 90,
    "regulatory": 180,
    "technology_trend": 45,
    "financial_forecast": 14,
    "product_demand": 60,
    "general": 120,
}


class DecayTracker:
    """
    Runs periodically (e.g., hourly). Checks all reality_validated beliefs
    for their trusted_until date and demotes those that have expired.
    """

    def __init__(self, firewall: "RealitySimulationFirewall"):
        self._firewall = firewall

    def compute_trusted_until(
        self,
        belief: "Belief",
        last_reality_contact: Optional[datetime] = None,
        domain: str = "general",
        claim_type: str = "general",
    ) -> datetime:
        """
        Compute when this belief's reality_validated status expires.
        Uses a half-life model: trusted_until = last_contact + half_life_days
        """
        half_life = DEFAULT_HALF_LIVES_DAYS.get(domain) or DEFAULT_HALF_LIVES_DAYS.get(claim_type) or DEFAULT_HALF_LIVES_DAYS["general"]
        contact = last_reality_contact or belief.promoted_at or datetime.now(timezone.utc)
        return contact + timedelta(days=half_life)

    def run_decay_cycle(self, now: Optional[datetime] = None) -> list[str]:
        """
        Check all reality_validated beliefs. Demote expired ones to provisional.
        Returns list of demoted belief_ids.
        """
        now = now or datetime.now(timezone.utc)
        demoted = []

        for belief in self._firewall._beliefs.values():
            if belief.validation_status != "reality_validated":
                continue

            trusted_until = self.compute_trusted_until(belief, belief.promoted_at)

            if now > trusted_until:
                old_status = belief.validation_status
                self._firewall.demote_to_provisional(
                    belief.belief_id,
                    reason=f"trusted_until={trusted_until.isoformat()} expired",
                )
                demoted.append(belief.belief_id)
                logger.warning(
                    "DECAY: belief %s demoted %s → provisional (trusted_until=%s, now=%s)",
                    belief.belief_id, old_status,
                    trusted_until.isoformat(), now.isoformat()
                )

        if demoted:
            logger.warning("DECAY CYCLE: %d beliefs demoted to provisional", len(demoted))
        else:
            logger.info("DECAY CYCLE: no beliefs expired")

        return demoted

    def days_until_expiry(
        self, belief: "Belief", last_reality_contact: Optional[datetime] = None
    ) -> float:
        trusted_until = self.compute_trusted_until(belief, last_reality_contact)
        delta = trusted_until - datetime.now(timezone.utc)
        return max(delta.total_seconds() / 86400, 0.0)
