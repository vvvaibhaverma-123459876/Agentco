"""
CFO-Agent V2 — Financial governance. claude-opus-4-8.

V2: pre-registers financial forecast claims, uses trusted_confidence() for spend decisions.
V1 thresholds preserved: auto-approve < $10k, human required > $50k.
Runway alert at 6 months (unchanged).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from runtime.base_agent.base_agent_v2 import BaseAgentV2, AgentActionV2
from runtime.escalation.escalation_gate import HumanApprovalRequired

logger = logging.getLogger(__name__)


class CFOAgentV2(BaseAgentV2):

    AGENT_ID = "cfo-agent"
    PROMPT_VERSION = "2.0.0"
    MODEL = "claude-opus-4-8"
    DEPARTMENT = "executive"

    CFO_AUTO_APPROVE_THRESHOLD = 10_000
    CFO_HUMAN_THRESHOLD = 50_000
    RUNWAY_ALERT_MONTHS = 6

    def __init__(self, calibration_engine: Optional[dict] = None):
        super().__init__(agent_id=self.AGENT_ID, calibration_engine=calibration_engine)

    def run(self, task: dict) -> Any:
        action_type = task.get("action_type", "")
        if action_type == "approve_spend":
            return self._handle_spend_approval(task)
        elif action_type == "runway_check":
            return self._handle_runway_check(task)
        elif action_type == "financial_forecast":
            return self._handle_financial_forecast(task)
        return {"status": "unknown_action"}

    def _handle_spend_approval(self, task: dict) -> dict:
        amount = task.get("amount", 0)
        purpose = task.get("purpose", "")

        if amount < self.CFO_AUTO_APPROVE_THRESHOLD:
            risk = "low"
        elif amount < self.CFO_HUMAN_THRESHOLD:
            risk = "medium"
        else:
            risk = "critical"

        action = AgentActionV2(
            action_type="approve_spend",
            description=f"Approve spend of ${amount:,} for: {purpose[:80]}",
            payload={"amount": amount, "purpose": purpose},
            risk_level=risk,
            stated_confidence=0.85,
            domain="financial_forecast",
            claim_type="spend_approval",
        )

        try:
            result = self.execute_action(action)
            return result
        except HumanApprovalRequired as exc:
            return {
                "status": "awaiting_human_approval",
                "override_id": exc.override_id,
                "amount": amount,
                "threshold": self.CFO_HUMAN_THRESHOLD,
                "message": f"Spend >${self.CFO_HUMAN_THRESHOLD:,} requires human approval.",
            }

    def _handle_runway_check(self, task: dict) -> dict:
        cash_balance = task.get("cash_balance", 0)
        monthly_burn = task.get("monthly_burn", 1)
        runway_months = cash_balance / monthly_burn if monthly_burn > 0 else float("inf")

        if runway_months <= self.RUNWAY_ALERT_MONTHS:
            logger.warning(
                "RUNWAY ALERT: %.1f months remaining (threshold=%d months)",
                runway_months, self.RUNWAY_ALERT_MONTHS
            )
            # Pre-register claim about fundraising timeline
            pid = self.pre_register_claim(
                claim=f"Company will secure additional funding within 90 days (runway={runway_months:.1f}mo)",
                probability=0.60,
                resolution_criterion="Term sheet signed or bridge loan closed within 90 days",
                resolution_date=datetime.now(timezone.utc) + timedelta(days=90),
                domain="financial_forecast",
                claim_type="runway_forecast",
                ground_truth_source="external_auditor",
            )
            return {
                "status": "runway_alert",
                "runway_months": runway_months,
                "prediction_id": pid,
                "action_required": "Immediate escalation to board required",
            }

        return {"status": "runway_ok", "runway_months": runway_months}

    def _handle_financial_forecast(self, task: dict) -> dict:
        forecast_value = task.get("forecast_value", 0)
        metric = task.get("metric", "revenue")
        horizon_days = task.get("horizon_days", 90)

        pid = self.pre_register_claim(
            claim=f"{metric} will reach ${forecast_value:,} within {horizon_days} days",
            probability=task.get("probability", 0.70),
            resolution_criterion=f"Audited {metric} figure at resolution_date",
            resolution_date=datetime.now(timezone.utc) + timedelta(days=horizon_days),
            domain="financial_forecast",
            claim_type="revenue_forecast",
            ground_truth_source="external_auditor",
        )
        return {"status": "forecast_registered", "prediction_id": pid}
