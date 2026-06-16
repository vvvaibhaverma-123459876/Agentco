"""Risk-Agent — risk register, cross-department monitoring, regulatory changes, risk reports."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class RiskAgent(BaseAgent):
    AGENT_ID = "risk-agent"
    DEPARTMENT = "legal"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "legal/risk"
    COMPETENCY_AREAS = ["risk_register", "regulatory_monitoring", "risk_reporting"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/legal/risk_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "assess_risk")
        messages = [{"role": "user", "content": f"Risk task: {task_type}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        risk_level = RiskLevel.HIGH if task.get("severity") == "critical" else RiskLevel.MEDIUM
        return AgentOutput(content=response, confidence_score=0.87, risk_level=risk_level, rationale=f"Risk assessment: {task_type}")
