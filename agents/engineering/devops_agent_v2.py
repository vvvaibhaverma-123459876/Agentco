"""
DevOps-Agent V2 — deployment and incident response. claude-sonnet-4-6.

V2: pre-registers deployment success claims, uses trusted_confidence().
Auto-rollback thresholds are hardcoded. Novel incidents → hard pause.
Rollback failure → immediate human escalation, no retry loop.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class DevOpsAgentV2(BaseAgentV2):

    AGENT_ID = "devops-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-sonnet-4-6"
    DEPARTMENT = "engineering"

    # Hardcoded — cannot be configured via prompts or config
    AUTO_ROLLBACK_ERROR_RATE = 0.05       # >5% error rate/5min triggers rollback
    AUTO_ROLLBACK_LATENCY_MULTIPLIER = 3.0  # >3x P99 triggers rollback
    AUTO_ROLLBACK_MEMORY_PCT = 0.90       # >90% memory/2min triggers rollback

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "deploy":
            return self._handle_deploy(task)
        elif action_type == "auto_rollback":
            return self._handle_auto_rollback(task)
        elif action_type == "novel_incident":
            return self._handle_novel_incident(task)
        elif action_type == "check_thresholds":
            return self._check_thresholds(task)
        return {"status": "unknown_action"}

    def _handle_deploy(self, task: dict) -> dict:
        version = task.get("version", "unknown")
        environment = task.get("environment", "production")

        pid = self.pre_register_claim(
            claim=f"Deployment of {version} to {environment} will succeed without triggering auto-rollback",
            probability=0.85,
            resolution_criterion=(
                f"No auto-rollback triggered within 30 minutes of deploy: "
                f"error_rate<{self.AUTO_ROLLBACK_ERROR_RATE:.0%}, "
                f"latency<{self.AUTO_ROLLBACK_LATENCY_MULTIPLIER}x P99, "
                f"memory<{self.AUTO_ROLLBACK_MEMORY_PCT:.0%}"
            ),
            resolution_date=datetime.now(timezone.utc) + timedelta(minutes=30),
            domain="engineering",
            claim_type="deployment",
            ground_truth_source="external_monitoring_system",
        )

        action = AgentActionV2(
            action_type="deploy",
            description=f"Deploy {version} to {environment}",
            payload={"version": version, "environment": environment, "prediction_id": pid},
            risk_level="high",
            stated_confidence=0.85,
            domain="engineering",
            claim_type="deployment",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "prediction_id": pid}

    def _handle_auto_rollback(self, task: dict) -> dict:
        trigger = task.get("trigger", "unknown")
        version = task.get("version", "unknown")
        rollback_failed = task.get("rollback_failed", False)

        if rollback_failed:
            logger.error("DEVOPS: ROLLBACK FAILED for version=%s trigger=%s — escalating to human", version, trigger)
            action = AgentActionV2(
                action_type="rollback_failed_escalation",
                description=f"CRITICAL: Rollback failed for {version} (trigger={trigger}). Immediate human intervention required.",
                payload={"version": version, "trigger": trigger, "rollback_failed": True},
                risk_level="critical",
                stated_confidence=1.0,
                domain="engineering",
                claim_type="incident_response",
            )
            try:
                result = self.execute_action(action)
                return result
            except HumanApprovalRequired as exc:
                return {"status": "human_escalation_required", "override_id": exc.override_id, "rollback_failed": True}

        action = AgentActionV2(
            action_type="auto_rollback",
            description=f"Auto-rollback triggered by {trigger} for version {version}",
            payload={"trigger": trigger, "version": version, "thresholds": {
                "error_rate": self.AUTO_ROLLBACK_ERROR_RATE,
                "latency_multiplier": self.AUTO_ROLLBACK_LATENCY_MULTIPLIER,
                "memory_pct": self.AUTO_ROLLBACK_MEMORY_PCT,
            }},
            risk_level="high",
            stated_confidence=0.95,
            domain="engineering",
            claim_type="incident_response",
        )

        try:
            result = self.execute_action(action)
            return {**result, "trigger": trigger}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id}

    def _handle_novel_incident(self, task: dict) -> dict:
        """Novel incident = hard pause. Never auto-resolve."""
        description = task.get("description", "")
        logger.error("DEVOPS: NOVEL INCIDENT — hard pause: %s", description)

        action = AgentActionV2(
            action_type="novel_incident_hard_pause",
            description=f"NOVEL INCIDENT — hard pause, human required: {description[:100]}",
            payload={"description": description, "auto_resolve": False},
            risk_level="critical",
            stated_confidence=0.99,
            domain="engineering",
            claim_type="incident_response",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "hard_pause_awaiting_human",
                "override_id": exc.override_id,
                "message": "Novel incident: system paused. Human intervention required. No auto-resolution.",
            }

    def _check_thresholds(self, task: dict) -> dict:
        error_rate = task.get("error_rate", 0.0)
        latency_multiplier = task.get("latency_multiplier", 1.0)
        memory_pct = task.get("memory_pct", 0.0)

        triggers = []
        if error_rate > self.AUTO_ROLLBACK_ERROR_RATE:
            triggers.append(f"error_rate={error_rate:.2%} > {self.AUTO_ROLLBACK_ERROR_RATE:.0%}")
        if latency_multiplier > self.AUTO_ROLLBACK_LATENCY_MULTIPLIER:
            triggers.append(f"latency={latency_multiplier:.1f}x > {self.AUTO_ROLLBACK_LATENCY_MULTIPLIER}x P99")
        if memory_pct > self.AUTO_ROLLBACK_MEMORY_PCT:
            triggers.append(f"memory={memory_pct:.0%} > {self.AUTO_ROLLBACK_MEMORY_PCT:.0%}")

        return {"should_rollback": len(triggers) > 0, "triggers": triggers}
