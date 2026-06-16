"""
Scenario-Agent — Step 2 of the 6-hour learning loop.

Takes a LearningSignal from Intelligence-Agent and generates hypotheses:
"If we adjusted the trust multiplier for domain X by Y%, calibration error would drop."

All hypotheses are PROVISIONAL. They:
- Do NOT modify any live agent behaviour
- Do NOT enter the firewall as reality_validated
- Are pre-registered as falsifiable claims in the ledger
- Require Trainer-Agent evaluation + human approval before any effect

The firewall guarantees: simulation hypotheses never cross to reality_validated.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    hypothesis_id: str
    domain: str
    description: str
    proposed_change: dict           # what would change if accepted
    expected_ece_improvement: float
    confidence: float
    prediction_id: Optional[str]    # pre-registered falsifiable claim
    status: str = "provisional"     # never "reality_validated" here


class ScenarioAgent(BaseAgentV2):

    AGENT_ID = "scenario-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-sonnet-4-6"
    DEPARTMENT = "learning"

    MAX_HYPOTHESES_PER_CYCLE = 5

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> dict:
        learning_signal = task.get("learning_signal", {})
        cycle_id = task.get("cycle_id", "unknown")
        return self.generate_hypotheses(learning_signal, cycle_id)

    def generate_hypotheses(self, learning_signal: dict, cycle_id: str) -> dict:
        focus_areas = learning_signal.get("recommended_focus_areas", [])
        degraded_agents = learning_signal.get("degraded_agents", [])
        surprise_patterns = learning_signal.get("surprise_patterns", [])

        hypotheses: list[Hypothesis] = []

        for domain in focus_areas[:self.MAX_HYPOTHESES_PER_CYCLE]:
            hyp_id = str(uuid.uuid4())
            # Pre-register the hypothesis as a falsifiable claim
            pid = self.pre_register_claim(
                claim=(
                    f"Increasing sample weight for domain '{domain}' calibration windows "
                    f"will reduce ECE by ≥0.02 over the next 30 days"
                ),
                probability=0.60,   # hypotheses have inherent uncertainty
                resolution_criterion=(
                    f"Measured ECE for domain '{domain}' drops ≥0.02 within 30 days "
                    "if hypothesis is accepted and applied"
                ),
                resolution_date=datetime.now(timezone.utc) + timedelta(days=30),
                domain=domain,
                claim_type="learning_hypothesis",
                ground_truth_source="external_calibration_auditor",
            )

            hyp = Hypothesis(
                hypothesis_id=hyp_id,
                domain=domain,
                description=f"Recalibrate trust weights for domain '{domain}' (ECE elevated)",
                proposed_change={
                    "type": "trust_weight_adjustment",
                    "domain": domain,
                    "direction": "increase_sample_recency_weight",
                },
                expected_ece_improvement=0.03,
                confidence=0.60,
                prediction_id=pid,
            )
            hypotheses.append(hyp)

        for agent_info in degraded_agents[:2]:
            hyp_id = str(uuid.uuid4())
            agent_id = agent_info.get("agent_id", "unknown")
            domain = agent_info.get("domain", "general")
            pid = self.pre_register_claim(
                claim=f"Agent '{agent_id}' will recover trust_factor > 0.5 in domain '{domain}' within 14 days with guided retraining",
                probability=0.55,
                resolution_criterion=f"trust_factor for {agent_id}/{domain} > 0.5 at resolution_date",
                resolution_date=datetime.now(timezone.utc) + timedelta(days=14),
                domain=domain,
                claim_type="agent_recovery",
                ground_truth_source="external_calibration_auditor",
            )
            hyp = Hypothesis(
                hypothesis_id=hyp_id,
                domain=domain,
                description=f"Guided retraining for degraded agent '{agent_id}' in domain '{domain}'",
                proposed_change={"type": "agent_retraining", "agent_id": agent_id, "domain": domain},
                expected_ece_improvement=0.05,
                confidence=0.55,
                prediction_id=pid,
            )
            hypotheses.append(hyp)

        hypotheses_dicts = [
            {
                "hypothesis_id": h.hypothesis_id,
                "domain": h.domain,
                "description": h.description,
                "proposed_change": h.proposed_change,
                "expected_ece_improvement": h.expected_ece_improvement,
                "confidence": h.confidence,
                "prediction_id": h.prediction_id,
                "status": h.status,
            }
            for h in hypotheses
        ]

        action = AgentActionV2(
            action_type="emit_hypotheses",
            description=f"Emit {len(hypotheses)} provisional hypotheses for cycle {cycle_id}",
            payload={"cycle_id": cycle_id, "hypotheses": hypotheses_dicts},
            risk_level="low",
            stated_confidence=0.65,
            domain="learning",
            claim_type="hypothesis_generation",
        )

        try:
            result = self.execute_action(action)
            return {
                "status": "hypotheses_ready",
                "cycle_id": cycle_id,
                "hypotheses": hypotheses_dicts,
                "count": len(hypotheses),
            }
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "hypotheses": hypotheses_dicts,
            }
