"""
CEO-Agent V2 — Strategic direction. claude-opus-4-8.

V2 additions: pre-registers forward claims, uses trusted_confidence(),
strategic pivots require human approval (unchanged from V1) + now also
blocked by EscalationGate when trusted_confidence < 0.50.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class CEOAgentV2(BaseAgentV2):

    AGENT_ID = "ceo-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-opus-4-8"
    DEPARTMENT = "executive"

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "strategic_pivot":
            return self._handle_strategic_pivot(task)
        elif action_type == "approve_budget":
            return self._handle_budget_approval(task)
        else:
            return {"status": "unknown_action"}

    def _handle_strategic_pivot(self, task: dict) -> dict:
        pivot_description = task.get("description", "")
        horizon_days = task.get("horizon_days", 90)

        # Pre-register: "This strategic direction will achieve stated goal"
        pid = self.pre_register_claim(
            claim=f"Strategic pivot will achieve stated objective within {horizon_days} days: {pivot_description[:100]}",
            probability=0.65,   # strategic pivots have inherent uncertainty
            resolution_criterion="Objective achieved as measured by agreed KPIs at resolution_date",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=horizon_days),
            domain="strategy",
            claim_type="strategic_decision",
            ground_truth_source="external_board_audit",
        )

        action = AgentActionV2(
            action_type="strategic_pivot",
            description=f"Strategic pivot: {pivot_description[:120]}",
            payload={
                "description": pivot_description,
                "horizon_days": horizon_days,
                "prediction_id": pid,
            },
            risk_level="critical",
            stated_confidence=0.65,
            domain="strategy",
            claim_type="strategic_decision",
            horizon_class="medium" if horizon_days <= 90 else "long",
        )

        try:
            result = self.execute_action(action, prediction_id=pid)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "prediction_id": pid,
                "message": "Strategic pivot requires human governor approval.",
            }

    def _handle_budget_approval(self, task: dict) -> dict:
        amount = task.get("amount", 0)
        risk = "critical" if amount > 500_000 else "high" if amount > 100_000 else "medium"

        action = AgentActionV2(
            action_type="approve_budget",
            description=f"Approve budget allocation of ${amount:,}",
            payload={"amount": amount, "purpose": task.get("purpose", "")},
            risk_level=risk,
            stated_confidence=0.80,
            domain="financial_forecast",
            claim_type="budget_decision",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "amount": amount,
                "message": f"Budget approval of ${amount:,} requires human governor approval.",
            }
