"""
Reviewer-Agent V2 — sole merge authority. claude-sonnet-4-6.

V2: pre-registers safety claims, uses trusted_confidence().
IS_SOLE_MERGE_AUTHORITY = True hardcoded. Zero tolerance for critical vulns.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class ReviewerAgentV2(BaseAgentV2):

    AGENT_ID = "reviewer-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-sonnet-4-6"
    DEPARTMENT = "engineering"

    IS_SOLE_MERGE_AUTHORITY = True
    MIN_TEST_COVERAGE = 0.95
    CRITICAL_VULN_TOLERANCE = 0   # zero tolerance

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "review":
            return self._handle_review(task)
        elif action_type == "merge":
            return self._handle_merge(task)
        elif action_type == "reject":
            return self._handle_reject(task)
        return {"status": "unknown_action"}

    def _handle_review(self, task: dict) -> dict:
        pr_id = task.get("pr_id", "unknown")
        coverage = task.get("test_coverage", 0.0)

        if coverage < self.MIN_TEST_COVERAGE:
            return {
                "status": "review_rejected",
                "reason": f"Test coverage {coverage:.0%} < required {self.MIN_TEST_COVERAGE:.0%}",
                "pr_id": pr_id,
            }

        pid = self.pre_register_claim(
            claim=f"PR {pr_id} is safe to merge and will not introduce regressions",
            probability=0.85,
            resolution_criterion="No P0/P1 incidents within 5 days of merge attributable to this PR",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=5),
            domain="engineering",
            claim_type="code_review",
            ground_truth_source="external_incident_tracker",
        )

        action = AgentActionV2(
            action_type="approve_review",
            description=f"Approve PR {pr_id} for merge",
            payload={"pr_id": pr_id, "test_coverage": coverage, "prediction_id": pid},
            risk_level="high",
            stated_confidence=0.85,
            domain="engineering",
            claim_type="code_review",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return {**result, "prediction_id": pid, "pr_id": pr_id}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "prediction_id": pid}

    def _handle_merge(self, task: dict) -> dict:
        pr_id = task.get("pr_id", "unknown")
        has_critical_vulns = task.get("has_critical_vulns", False)

        if has_critical_vulns:
            logger.error("REVIEWER: merge blocked — critical vulnerabilities present in PR %s", pr_id)
            return {
                "status": "merge_blocked",
                "reason": "Zero tolerance for critical vulnerabilities. Fix before merge.",
                "pr_id": pr_id,
            }

        action = AgentActionV2(
            action_type="merge_pr",
            description=f"Merge PR {pr_id} (Reviewer-Agent sole authority)",
            payload={"pr_id": pr_id},
            risk_level="critical",
            stated_confidence=0.90,
            domain="engineering",
            claim_type="merge_decision",
        )

        try:
            result = self.execute_action(action)
            return {**result, "pr_id": pr_id}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id, "pr_id": pr_id}

    def _handle_reject(self, task: dict) -> dict:
        pr_id = task.get("pr_id", "unknown")
        reason = task.get("reason", "")
        action = AgentActionV2(
            action_type="reject_pr",
            description=f"Reject PR {pr_id}: {reason[:80]}",
            payload={"pr_id": pr_id, "reason": reason},
            risk_level="medium",
            stated_confidence=0.90,
            domain="engineering",
            claim_type="code_review",
        )
        try:
            result = self.execute_action(action)
            return {**result, "pr_id": pr_id}
        except HumanApprovalRequired as exc:
            return {"status": "awaiting_human_approval", "override_id": exc.override_id}
