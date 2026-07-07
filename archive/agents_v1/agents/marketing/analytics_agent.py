"""Analytics-Agent — marketing dashboards, attribution, funnel analysis, data quality."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class AnalyticsAgent(BaseAgent):
    AGENT_ID = "analytics-agent"
    DEPARTMENT = "marketing"
    MEMORY_NAMESPACE = "marketing/analytics"
    COMPETENCY_AREAS = ["attribution", "funnel_analysis", "data_quality", "dashboards"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/marketing/analytics_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        messages = [{"role": "user", "content": f"Analytics task: {task.get('type', 'dashboard')}\nData: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale=f"Analytics: {task.get('type', 'general')}")
