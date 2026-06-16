"""
Synthesis-Agent — cross-domain pattern discovery. claude-opus-4-8.

Reads principles from multiple domains and identifies cross-domain patterns.
All synthesis outputs enter the Principle Library as provisional.
Uses Theory Engine to register testable predictions for each principle.

INVARIANT: Synthesis-Agent cannot validate its own principles.
           All outputs are provisional until external reality contact.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class SynthesisAgent(BaseAgentV2):

    AGENT_ID = "synthesis-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-opus-4-8"
    DEPARTMENT = "synthesis"

    def __init__(
        self,
        calibration_engine: Optional[dict] = None,
        principle_library=None,
        theory_engine=None,
    ):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)
        self._library = principle_library
        self._theory = theory_engine

    def run(self, task: dict) -> dict:
        action_type = task.get("action_type", "")
        if action_type == "synthesize":
            return self._handle_synthesis(task)
        elif action_type == "query_principles":
            return self._query_principles(task)
        return {"status": "unknown_action"}

    def _handle_synthesis(self, task: dict) -> dict:
        """
        Discover cross-domain patterns from provided observations.
        All outputs enter as provisional; Theory Engine registers test predictions.
        """
        observations = task.get("observations", [])
        domains = task.get("domains", ["general"])
        synthesis_description = task.get("synthesis", "Cross-domain pattern detected")

        # Add principle to library (always provisional)
        principle = None
        belief_registration = None

        if self._library:
            principle = self._library.add_principle(
                title=task.get("title", "Unnamed principle"),
                description=synthesis_description,
                source_domains=domains,
                confidence=0.55,   # synthesis starts with low confidence
                evidence_prediction_ids=[],
            )

            # Register with Theory Engine for testability
            if self._theory and principle:
                test_claims = task.get("test_claims", [
                    {
                        "claim": f"Principle '{principle.title}' will be confirmed in domain '{domains[0]}' within 30 days",
                        "probability": 0.60,
                        "resolution_criterion": f"External auditor confirms pattern holds in {domains[0]}",
                        "ground_truth_source": "external_auditor",
                        "horizon_days": 30,
                    }
                ])
                belief_registration = self._theory.register_principle_for_testing(principle, test_claims)

        action = AgentActionV2(
            action_type="emit_synthesis",
            description=f"Emit cross-domain synthesis across {domains}: {synthesis_description[:80]}",
            payload={
                "domains": domains,
                "synthesis": synthesis_description,
                "principle_id": principle.principle_id if principle else None,
                "belief_id": belief_registration.get("belief_id") if belief_registration else None,
                "validation_status": "provisional",
            },
            risk_level="medium",
            stated_confidence=0.55,
            domain="synthesis",
            claim_type="cross_domain_principle",
            horizon_class="medium",
        )

        try:
            result = self.execute_action(action)
            return {
                "status": "synthesis_emitted",
                "principle_id": principle.principle_id if principle else None,
                "belief_id": belief_registration.get("belief_id") if belief_registration else None,
                "validation_status": "provisional",
                "belief_registration": belief_registration,
                "note": (
                    "Synthesis output is provisional. Will remain so until test predictions "
                    "resolve TRUE via external ground truth through Resolution Service."
                ),
            }
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "principle_id": principle.principle_id if principle else None,
            }

    def _query_principles(self, task: dict) -> dict:
        domain = task.get("domain")
        status = task.get("status")
        if not self._library:
            return {"principles": [], "note": "No principle library wired"}

        if domain:
            principles = self._library.list_by_domain(domain)
        elif status:
            principles = self._library.list_by_status(status)
        else:
            principles = self._library.list_by_status("provisional") + self._library.list_by_status("reality_validated")

        return {
            "principles": [
                {
                    "principle_id": p.principle_id,
                    "title": p.title,
                    "domains": p.source_domains,
                    "validation_status": p.validation_status,
                    "confidence": p.confidence,
                }
                for p in principles
            ],
            "count": len(principles),
        }
