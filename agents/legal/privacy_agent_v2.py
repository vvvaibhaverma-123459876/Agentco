"""
Privacy-Agent V2 — data protection and breach response. claude-opus-4-8.

V2: pre-registers compliance claims, uses trusted_confidence().
AUTONOMOUS_REMEDIATION = False hardcoded. Breach response ALWAYS blocks.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class PrivacyAgentV2(BaseAgentV2):

    AGENT_ID = "privacy-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-opus-4-8"
    DEPARTMENT = "legal"

    AUTONOMOUS_REMEDIATION = False   # Hardcoded. Never auto-remediate a breach.

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "breach_response":
            return self._handle_breach_response(task)
        elif action_type == "compliance_check":
            return self._handle_compliance_check(task)
        elif action_type == "data_access_request":
            return self._handle_data_access_request(task)
        return {"status": "unknown_action"}

    def _handle_breach_response(self, task: dict) -> dict:
        """
        Breach response is ALWAYS blocked for human decision.
        AUTONOMOUS_REMEDIATION = False means no action proceeds without human.
        """
        breach_type = task.get("breach_type", "unknown")
        affected_records = task.get("affected_records", 0)

        if self.AUTONOMOUS_REMEDIATION:
            # This branch should be unreachable — defensive assertion
            raise RuntimeError("INVARIANT VIOLATION: AUTONOMOUS_REMEDIATION cannot be True")

        logger.error(
            "PRIVACY BREACH DETECTED: type=%s affected_records=%d — IMMEDIATE ESCALATION",
            breach_type, affected_records
        )

        action = AgentActionV2(
            action_type="breach_response",
            description=(
                f"DATA BREACH [{breach_type}]: {affected_records} records affected. "
                "Immediate human decision required. No autonomous remediation."
            ),
            payload={
                "breach_type": breach_type,
                "affected_records": affected_records,
                "autonomous_remediation": False,
                "notify": ["legal-agent", "ceo-agent", "coo-agent"],
            },
            risk_level="critical",
            stated_confidence=0.99,
            domain="legal",
            claim_type="breach_response",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "breach_escalated_awaiting_human",
                "override_id": exc.override_id,
                "breach_type": breach_type,
                "affected_records": affected_records,
                "autonomous_remediation": False,
                "message": "Breach detected. All remediation requires human decision. System escalated.",
            }

    def _handle_compliance_check(self, task: dict) -> dict:
        regulation = task.get("regulation", "")
        scope = task.get("scope", "")

        pid = self.pre_register_claim(
            claim=f"System is compliant with {regulation} for scope: {scope}",
            probability=task.get("probability", 0.85),
            resolution_criterion=f"External auditor confirms {regulation} compliance within 30 days",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=30),
            domain="legal",
            claim_type="compliance_assessment",
            ground_truth_source="external_auditor",
        )

        action = AgentActionV2(
            action_type="compliance_check",
            description=f"Compliance check: {regulation} — scope: {scope[:60]}",
            payload={"regulation": regulation, "scope": scope, "prediction_id": pid},
            risk_level="medium",
            stated_confidence=0.85,
            domain="legal",
            claim_type="compliance_assessment",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "prediction_id": pid}

    def _handle_data_access_request(self, task: dict) -> dict:
        requester = task.get("requester", "unknown")
        data_type = task.get("data_type", "unknown")

        action = AgentActionV2(
            action_type="data_access_request",
            description=f"Data access request from {requester} for {data_type}",
            payload={"requester": requester, "data_type": data_type},
            risk_level="high",
            stated_confidence=0.80,
            domain="legal",
            claim_type="data_governance",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id}
