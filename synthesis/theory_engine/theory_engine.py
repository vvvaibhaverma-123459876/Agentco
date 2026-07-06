"""
Theory Engine — routes principles through the Reality/Simulation Firewall.

When Synthesis-Agent produces a new cross-domain principle:
1. Theory Engine creates a belief in the Firewall (starts provisional)
2. Pre-registers testable predictions that would confirm the principle
3. The principle stays provisional until those predictions resolve TRUE
   via the Resolution Service with external ground truth

INVARIANT: Theory Engine cannot promote its own beliefs.
           It creates the belief and the test predictions.
           Promotion only happens via ResolutionService → Firewall.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from calibration.firewall.firewall import RealitySimulationFirewall
    from calibration.ledger.prediction_ledger import PredictionLedger
    from synthesis.principle_library.principle_library import PrincipleLibrary, Principle

logger = logging.getLogger(__name__)


class TheoryEngine:

    def __init__(
        self,
        firewall: Optional["RealitySimulationFirewall"] = None,
        ledger: Optional["PredictionLedger"] = None,
        principle_library: Optional["PrincipleLibrary"] = None,
    ):
        self._firewall = firewall
        self._ledger = ledger
        self._library = principle_library

    def register_principle_for_testing(
        self,
        principle: "Principle",
        test_claims: list[dict],
    ) -> dict:
        """
        For each principle from Synthesis-Agent:
        1. Create a provisional belief in the Firewall
        2. Pre-register the test claims as predictions in the Ledger

        The principle stays provisional until at least 3 predictions resolve
        TRUE via external ground truth (the standard firewall gate).
        """
        if not self._firewall or not self._ledger:
            return {"status": "no_firewall_or_ledger"}

        from calibration.firewall.firewall import Belief
        from calibration.ledger.prediction_ledger import PredictionRegistration

        # Step 1: Create provisional belief in firewall
        belief = Belief(
            belief_id=str(__import__("uuid").uuid4()),
            statement=principle.description[:200],
            origin="synthesis-agent",
            validation_status="provisional",
        )
        self._firewall.register_belief(belief)
        logger.info(
            "THEORY ENGINE: created provisional belief %s for principle %s",
            belief.belief_id, principle.principle_id
        )

        # Step 2: Pre-register test predictions
        prediction_ids = []
        for claim_spec in test_claims:
            try:
                reg = PredictionRegistration(
                    claim=claim_spec["claim"],
                    probability=claim_spec.get("probability", 0.65),
                    confidence_basis={
                        "principle_id": principle.principle_id,
                        "theory_engine": "cross_domain_synthesis_test",
                    },
                    producing_agent_id="synthesis-agent",
                    producing_prompt_version="2.0.0",
                    resolution_criterion=claim_spec["resolution_criterion"],
                    resolution_date=datetime.now(timezone.utc) + timedelta(
                        days=claim_spec.get("horizon_days", 30)
                    ),
                    ground_truth_source=claim_spec.get("ground_truth_source", "external_auditor"),
                    horizon_class=claim_spec.get("horizon_class", "short"),
                    domain=principle.source_domains[0] if principle.source_domains else "general",
                    claim_type="principle_test",
                )
                pid = self._ledger.pre_register(reg)
                prediction_ids.append(pid)
            except Exception as e:
                logger.warning("THEORY ENGINE: failed to register claim: %s", e)

        return {
            "belief_id": belief.belief_id,
            "validation_status": "provisional",
            "prediction_ids": prediction_ids,
            "status": "registered_for_testing",
            "note": (
                "This principle is provisional. It will remain so until "
                f"{len(prediction_ids)} test predictions resolve TRUE via "
                "external ground truth. Theory Engine cannot self-promote."
            ),
        }

    def check_promotion_readiness(self, belief_id: str) -> dict:
        """Check whether a belief meets the firewall's promotion gate."""
        if not self._firewall:
            return {"ready": False, "reason": "no_firewall"}
        belief = self._firewall._beliefs.get(belief_id)
        if not belief:
            return {"ready": False, "reason": "belief_not_found"}
        return {
            "belief_id": belief_id,
            "current_status": belief.validation_status,
            "ready": belief.validation_status == "reality_validated",
            "sim_support_count": belief.sim_support_count,
            "note": "sim_support_count is intentionally excluded from the promotion gate.",
        }
