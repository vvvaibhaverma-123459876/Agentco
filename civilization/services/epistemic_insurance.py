"""Epistemic insurance: escrow verification (Phase 8)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class EpistemicInsuranceManager:
    """Allocate escrow for high-stakes claims."""

    def allocate_escrow(self, claim_id: str, verification_budget: int) -> dict:
        """
        Allocate escrow for verification.

        Schedule: initial 30%, follow-up 30%, option 40%
        """
        initial = int(verification_budget * 0.3)
        followup = int(verification_budget * 0.3)
        option = verification_budget - initial - followup

        return {
            "claim_id": claim_id,
            "initial_escrow": initial,
            "followup_escrow": followup,
            "option_value": option,
            "schedule": ["day_0", "day_30", "day_90"],
        }
