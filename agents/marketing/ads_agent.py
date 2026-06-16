"""Ads-Agent — campaign management, budget optimisation. Cannot increase total budget without CFO approval."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class AdsAgent(BaseAgent):
    AGENT_ID = "ads-agent"
    DEPARTMENT = "marketing"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "marketing/ads"
    COMPETENCY_AREAS = ["campaign_management", "budget_optimisation", "bid_management"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/marketing/ads_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        if task.get("type") == "increase_total_budget":
            return AgentOutput(content={"blocked": True, "reason": "Total budget increase requires CFO-Agent approval"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="HARD CONSTRAINT: Cannot increase total spend budget without CFO-Agent approval")

        messages = [{"role": "user", "content": f"Ads task: {task.get('type', 'optimize')}\nApproved budget: {task.get('approved_budget')}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="Campaign management within approved budget")
