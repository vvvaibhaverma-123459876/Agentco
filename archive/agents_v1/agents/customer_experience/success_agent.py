"""Success-Agent — health monitoring, churn intervention, onboarding, expansion identification."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class SuccessAgent(BaseAgent):
    AGENT_ID = "success-agent"
    DEPARTMENT = "customer_experience"
    MEMORY_NAMESPACE = "cx/success"
    COMPETENCY_AREAS = ["health_monitoring", "churn_intervention", "onboarding", "expansion"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/customer_experience/success_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        messages = [{"role": "user", "content": f"Customer success task: {task.get('type', 'health_check')}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale=f"Customer success: {task.get('type', 'general')}")
