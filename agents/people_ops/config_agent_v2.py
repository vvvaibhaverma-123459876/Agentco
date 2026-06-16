"""
Config-Agent V2 — CRITICAL RISK. Manages prompts and permissions for ALL agents.

V2 contract additions (on top of V1 hardcoded rules):
- Inherits BaseAgentV2: all actions use trusted_confidence(), pre-registers claims
- EVERY action still requires human approval — EVERY_ACTION_REQUIRES_HUMAN_APPROVAL is True
- Cannot modify its own prompt (enforced in execute_config_action)
- Staged rollout: 5% → 25% → 100%
- Rollback to any version in <60 seconds
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class ConfigAgentV2(BaseAgentV2):

    AGENT_ID = "config-agent"
    PROMPT_VERSION = "2.0.0"
    DEPARTMENT = "people_ops"

    # HARDCODED — never in prompts, never configurable
    EVERY_ACTION_REQUIRES_HUMAN_APPROVAL = True
    ROLLOUT_STAGES = [0.05, 0.25, 1.00]   # 5% → 25% → 100%
    ROLLBACK_SLA_SECONDS = 60
    OWN_PROMPT_IDS = {"config_agent_v1.0.0.md", "config_agent_v2.0.0.md"}

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "update_prompt":
            return self._handle_prompt_update(task)
        elif action_type == "rollback":
            return self._handle_rollback(task)
        elif action_type == "update_permissions":
            return self._handle_permission_update(task)
        else:
            logger.warning("ConfigAgentV2: unknown action_type=%s", action_type)
            return {"status": "unknown_action"}

    def _handle_prompt_update(self, task: dict) -> dict:
        target_agent = task.get("target_agent_id", "")

        # INVARIANT: Cannot modify own prompt — hardcoded, not in prompts
        if target_agent == self.AGENT_ID:
            logger.error(
                "CONFIG-AGENT SELF-MODIFICATION BLOCKED: agent=%s attempted to modify own prompt",
                self.AGENT_ID
            )
            return {
                "status": "blocked",
                "reason": "Config-Agent cannot modify its own prompt. This is a hardcoded invariant.",
            }

        new_version = task.get("new_prompt_version", "unknown")

        # Pre-register the claim: "This prompt update will not degrade performance"
        pid = self.pre_register_claim(
            claim=f"Prompt update to {target_agent} version {new_version} will not degrade agent performance metrics",
            probability=0.80,
            resolution_criterion=f"Agent {target_agent} performance metrics within 5% of baseline after 7 days",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=7),
            domain="engineering",
            claim_type="config_change",
            ground_truth_source="external_monitoring_system",
        )

        action = AgentActionV2(
            action_type="update_prompt",
            description=f"Update prompt for {target_agent} to version {new_version}",
            payload={
                "target_agent_id": target_agent,
                "new_prompt_version": new_version,
                "rollout_stages": self.ROLLOUT_STAGES,
            },
            risk_level="critical",   # ALL config changes are critical
            stated_confidence=0.80,
            domain="engineering",
            claim_type="config_change",
        )

        # EVERY_ACTION_REQUIRES_HUMAN_APPROVAL — will always raise unless pre-approved
        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "rollout_stages": self.ROLLOUT_STAGES}
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "risk_level": exc.risk_level,
                "prediction_id": pid,
                "message": "Human approval required before prompt update can proceed.",
            }

    def _handle_rollback(self, task: dict) -> dict:
        target_agent = task.get("target_agent_id", "")
        target_version = task.get("target_version", "")

        action = AgentActionV2(
            action_type="rollback_prompt",
            description=f"Rollback {target_agent} to prompt version {target_version}",
            payload={
                "target_agent_id": target_agent,
                "target_version": target_version,
                "sla_seconds": self.ROLLBACK_SLA_SECONDS,
            },
            risk_level="critical",
            stated_confidence=0.90,   # rollbacks are well-understood operations
            domain="engineering",
            claim_type="config_rollback",
        )

        try:
            result = self.execute_action(action)
            return {**result, "rollback_sla_seconds": self.ROLLBACK_SLA_SECONDS}
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "risk_level": exc.risk_level,
                "message": "Human approval required before rollback can proceed.",
            }

    def _handle_permission_update(self, task: dict) -> dict:
        target_agent = task.get("target_agent_id", "")
        permission_change = task.get("permission_change", {})

        action = AgentActionV2(
            action_type="update_permissions",
            description=f"Update permissions for {target_agent}: {permission_change}",
            payload={
                "target_agent_id": target_agent,
                "permission_change": permission_change,
            },
            risk_level="critical",
            stated_confidence=0.75,
            domain="engineering",
            claim_type="permission_change",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "risk_level": exc.risk_level,
                "message": "Human approval required before permission update can proceed.",
            }
