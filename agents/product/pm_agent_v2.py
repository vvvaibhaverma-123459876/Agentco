"""
PM-Agent V2 — product prioritization and scope approval.

V2: pre-registers feature delivery claims, uses trusted_confidence().
Scope approvals for engineering agents go through escalation gate.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class PMAgentV2(BaseAgentV2):

    AGENT_ID = "pm-agent"
    PROMPT_VERSION = "2.0.0"
    DEPARTMENT = "product"

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "feature_prioritization":
            return self._handle_feature_prioritization(task)
        elif action_type == "scope_approval":
            return self._handle_scope_approval(task)
        elif action_type == "roadmap_update":
            return self._handle_roadmap_update(task)
        return {"status": "unknown_action"}

    def _handle_feature_prioritization(self, task: dict) -> dict:
        feature = task.get("feature", "")
        horizon_days = task.get("horizon_days", 30)

        pid = self.pre_register_claim(
            claim=f"Feature '{feature}' will ship within {horizon_days} days as prioritized",
            probability=task.get("probability", 0.75),
            resolution_criterion=f"Feature shipped and in production within {horizon_days} days",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=horizon_days),
            domain="product",
            claim_type="feature_delivery",
            ground_truth_source="external_release_tracker",
        )

        action = AgentActionV2(
            action_type="prioritize_feature",
            description=f"Prioritize feature '{feature}' for {horizon_days}d horizon",
            payload={"feature": feature, "horizon_days": horizon_days, "prediction_id": pid},
            risk_level="medium",
            stated_confidence=0.75,
            domain="product",
            claim_type="feature_delivery",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "prediction_id": pid}

    def _handle_scope_approval(self, task: dict) -> dict:
        requesting_agent = task.get("requesting_agent", "unknown")
        scope_description = task.get("description", "")

        action = AgentActionV2(
            action_type="approve_scope_change",
            description=f"Approve scope change from {requesting_agent}: {scope_description[:80]}",
            payload={"requesting_agent": requesting_agent, "description": scope_description},
            risk_level="high",
            stated_confidence=0.80,
            domain="product",
            claim_type="scope_decision",
        )

        try:
            result = self.execute_action(action)
            return {**result, "approved": True}
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "requesting_agent": requesting_agent,
            }

    def _handle_roadmap_update(self, task: dict) -> dict:
        changes = task.get("changes", [])
        action = AgentActionV2(
            action_type="update_roadmap",
            description=f"Update product roadmap ({len(changes)} changes)",
            payload={"changes": changes},
            risk_level="medium",
            stated_confidence=0.80,
            domain="product",
            claim_type="roadmap_decision",
        )
        try:
            return self.execute_action(action)
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id}
