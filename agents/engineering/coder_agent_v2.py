"""
Coder-Agent V2 — writes code, never merges. claude-sonnet-4-6.

V2: pre-registers code quality claims, uses trusted_confidence().
CAN_MERGE = False is hardcoded. Scope changes require PM-Agent approval.
Security alerts always block for human review.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class CoderAgentV2(BaseAgentV2):

    AGENT_ID = "coder-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-sonnet-4-6"
    DEPARTMENT = "engineering"

    CAN_MERGE = False   # Hardcoded. Reviewer-Agent is the sole merge authority.

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "write_code":
            return self._handle_write_code(task)
        elif action_type == "scope_change":
            return self._handle_scope_change(task)
        elif action_type == "security_alert":
            return self._handle_security_alert(task)
        elif action_type == "merge":
            return {"status": "blocked", "reason": "CAN_MERGE=False. Coder-Agent cannot merge. Use Reviewer-Agent."}
        return {"status": "unknown_action"}

    def _handle_write_code(self, task: dict) -> dict:
        description = task.get("description", "")
        ticket_id = task.get("ticket_id", "unknown")

        pid = self.pre_register_claim(
            claim=f"Code for {ticket_id} will pass automated tests and peer review without critical issues",
            probability=0.80,
            resolution_criterion="PR passes CI, no critical findings in review, merged within 5 days",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=5),
            domain="engineering",
            claim_type="code_quality",
            ground_truth_source="external_ci_and_reviewer",
        )

        action = AgentActionV2(
            action_type="write_code",
            description=f"Write code for {ticket_id}: {description[:80]}",
            payload={"ticket_id": ticket_id, "description": description, "prediction_id": pid},
            risk_level="medium",
            stated_confidence=0.80,
            domain="engineering",
            claim_type="code_quality",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "prediction_id": pid}

    def _handle_scope_change(self, task: dict) -> dict:
        description = task.get("description", "")
        # Scope change requires PM-Agent approval → critical risk
        action = AgentActionV2(
            action_type="scope_change",
            description=f"Scope change request (requires PM-Agent approval): {description[:100]}",
            payload={"description": description, "requires_pm_approval": True},
            risk_level="critical",
            stated_confidence=0.70,
            domain="engineering",
            claim_type="scope_change",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_pm_and_human_approval",
                "override_id": exc.override_id,
                "message": "Scope change requires PM-Agent + human governor approval.",
            }

    def _handle_security_alert(self, task: dict) -> dict:
        severity = task.get("severity", "unknown")
        description = task.get("description", "")
        # Security alerts always block — no auto-remediation
        action = AgentActionV2(
            action_type="security_alert",
            description=f"SECURITY ALERT [{severity}]: {description[:100]}",
            payload={"severity": severity, "description": description, "notify": ["reviewer-agent", "risk-agent"]},
            risk_level="critical",
            stated_confidence=0.95,   # high confidence it IS a security issue
            domain="engineering",
            claim_type="security_vulnerability",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_review",
                "override_id": exc.override_id,
                "severity": severity,
                "message": "Security alert requires immediate human review before any action.",
            }
