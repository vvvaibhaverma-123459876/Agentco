"""UX-Agent — user flows, wireframes, accessibility compliance."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class UXAgent(BaseAgent):
    AGENT_ID = "ux-agent"
    DEPARTMENT = "design"
    MEMORY_NAMESPACE = "design/ux"
    COMPETENCY_AREAS = ["user_flows", "wireframing", "accessibility", "design_handoff"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/design/ux_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        messages = [{"role": "user", "content": f"UX task: {task_type}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale=f"UX design task: {task_type}")
