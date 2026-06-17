"""CFO-Agent — real-time financial oversight, spend approval, runway monitoring."""
from __future__ import annotations

import os
from typing import Any

from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


SPEND_THRESHOLD_AUTO_APPROVE = float(os.environ.get("CFO_AUTO_APPROVE_THRESHOLD", "10000"))
SPEND_THRESHOLD_HUMAN = float(os.environ.get("CFO_HUMAN_THRESHOLD", "50000"))
RUNWAY_ALERT_MONTHS = int(os.environ.get("CFO_RUNWAY_ALERT_MONTHS", "6"))


class CFOAgent(BaseAgent):
    AGENT_ID = "cfo-agent"
    DEPARTMENT = "executive"
    MEMORY_NAMESPACE = "executive/cfo"
    COMPETENCY_AREAS = ["financial_monitoring", "spend_approval", "forecasting", "runway"]
    AUTONOMY_LEVEL = "medium"

    def get_system_prompt(self) -> str:
        with open("agents/prompts/executive/cfo_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "spend_request":
            return await self._evaluate_spend_request(task)
        elif task_type == "runway_check":
            return await self._check_runway(task)
        elif task_type == "cost_anomaly":
            return await self._handle_cost_anomaly(task)
        else:
            return await self._financial_monitoring(task)

    async def _evaluate_spend_request(self, task: dict) -> AgentOutput:
        amount = task.get("amount", 0)
        dept_budget = task.get("department_budget", 0)
        overage_pct = ((amount - dept_budget) / dept_budget * 100) if dept_budget else 0

        messages = [{"role": "user", "content": f"Evaluate spend request: ${amount} (budget: ${dept_budget}, overage: {overage_pct:.1f}%)\nReason: {task.get('reason', '')}"}]
        response = await self.llm_call(messages)

        if amount <= SPEND_THRESHOLD_AUTO_APPROVE or overage_pct <= 0:
            return AgentOutput(content={"decision": "approved", "amount": amount, "rationale": response}, confidence_score=0.95, risk_level=RiskLevel.LOW, rationale="Within auto-approval threshold")
        elif amount > SPEND_THRESHOLD_HUMAN or overage_pct > 25:
            return AgentOutput(content={"decision": "pending_human", "amount": amount}, confidence_score=0.90, risk_level=RiskLevel.CRITICAL, rationale="Exceeds absolute threshold — human approval required", requires_human_approval=True, escalation_reason="Spend exceeds configured threshold")
        else:
            # 10–25% over: approve with flag to COO
            await self.publish_event(AgentEvent(event_type="finance.spend.flagged", producer_agent_id=self.AGENT_ID, confidence_score=0.90, payload={"amount": amount, "overage_pct": overage_pct, "agent_id": task.get("requesting_agent_id")}, risk_level=RiskLevel.MEDIUM, requires_ack=False))
            return AgentOutput(content={"decision": "approved_with_flag", "amount": amount}, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale="Approved with COO notification")

    async def _check_runway(self, task: dict) -> AgentOutput:
        runway_months = task.get("runway_months", 12)
        burn_rate = task.get("burn_rate", 0)
        current_arr = task.get("current_arr", 0)

        if runway_months <= RUNWAY_ALERT_MONTHS:
            await self.publish_event(AgentEvent(event_type="finance.runway.alert", producer_agent_id=self.AGENT_ID, confidence_score=0.99, payload={"runway_months": runway_months, "burn_rate": burn_rate, "current_arr": current_arr}, risk_level=RiskLevel.CRITICAL, requires_ack=True))
            return AgentOutput(content={"runway_months": runway_months, "alert": True}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale=f"Runway below {RUNWAY_ALERT_MONTHS} months — critical escalation", requires_human_approval=True, escalation_reason="Runway alert: immediate human review required")

        return AgentOutput(content={"runway_months": runway_months, "status": "healthy"}, confidence_score=0.97, risk_level=RiskLevel.LOW, rationale="Runway within safe parameters")

    async def _handle_cost_anomaly(self, task: dict) -> AgentOutput:
        await self.publish_event(AgentEvent(event_type="finance.spend.flagged", producer_agent_id=self.AGENT_ID, confidence_score=0.92, payload=task, risk_level=RiskLevel.HIGH, requires_ack=True))
        return AgentOutput(content={"anomaly": task, "alerted": True}, confidence_score=0.92, risk_level=RiskLevel.HIGH, rationale="Cost anomaly detected and escalated")

    async def _financial_monitoring(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Financial monitoring task: {task}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale="Routine financial monitoring")
