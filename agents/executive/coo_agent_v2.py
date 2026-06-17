"""
COO-Agent V2 — Operations and execution.

V2: pre-registers operational targets, uses trusted_confidence() for risk decisions.
Structural changes still require CEO-Agent approval (unchanged from V1).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class COOAgentV2(BaseAgentV2):

    AGENT_ID = "coo-agent"
    PROMPT_VERSION = "2.0.0"
    DEPARTMENT = "executive"

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "structural_change":
            return self._handle_structural_change(task)
        elif action_type == "operational_target":
            return self._handle_operational_target(task)
        return {"status": "unknown_action"}

    def _handle_structural_change(self, task: dict) -> dict:
        description = task.get("description", "")

        # Pre-register: structural change outcome claim
        pid = self.pre_register_claim(
            claim=f"Structural change will improve operational efficiency: {description[:100]}",
            probability=0.70,
            resolution_criterion="Operational metrics improve by ≥10% within 60 days post-change",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=60),
            domain="operations",
            claim_type="structural_change",
            ground_truth_source="external_auditor",
        )

        action = AgentActionV2(
            action_type="structural_change",
            description=f"Structural change (requires CEO approval): {description[:100]}",
            payload={"description": description, "prediction_id": pid},
            risk_level="critical",   # structural changes always require CEO + human approval
            stated_confidence=0.70,
            domain="operations",
            claim_type="structural_change",
            horizon_class="medium",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_ceo_and_human_approval",
                "override_id": exc.override_id,
                "prediction_id": pid,
                "message": "Structural changes require CEO-Agent + human governor approval.",
            }

    def _handle_operational_target(self, task: dict) -> dict:
        metric = task.get("metric", "")
        target_value = task.get("target_value", 0)
        horizon_days = task.get("horizon_days", 30)

        pid = self.pre_register_claim(
            claim=f"Operational metric '{metric}' will reach {target_value} within {horizon_days} days",
            probability=task.get("probability", 0.75),
            resolution_criterion=f"Measured {metric} ≥ {target_value} at resolution_date",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=horizon_days),
            domain="operations",
            claim_type="operational_target",
            ground_truth_source="external_monitoring_system",
        )

        action = AgentActionV2(
            action_type="set_operational_target",
            description=f"Set target: {metric} = {target_value} in {horizon_days}d",
            payload={"metric": metric, "target_value": target_value, "horizon_days": horizon_days},
            risk_level="medium",
            stated_confidence=0.75,
            domain="operations",
            claim_type="operational_target",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid}
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "prediction_id": pid,
            }
