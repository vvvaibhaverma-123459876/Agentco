"""Brand-Agent — design system owner, brand compliance, tone of voice."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class BrandAgent(BaseAgent):
    AGENT_ID = "brand-agent"
    DEPARTMENT = "design"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "design/brand"
    COMPETENCY_AREAS = ["design_system", "brand_compliance", "tone_of_voice"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/design/brand_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "compliance_review")
        messages = [{"role": "user", "content": f"Brand review: {task_type}\nContent: {task.get('content', task)}"}]
        response = await self.llm_call(messages, self.get_tools())
        compliant = "non-compliant" not in str(response).lower()
        return AgentOutput(
            content={"review": response, "compliant": compliant, "can_publish": compliant},
            confidence_score=0.90,
            risk_level=RiskLevel.LOW if compliant else RiskLevel.HIGH,
            rationale=f"Brand compliance: {'PASS' if compliant else 'FAIL — blocked from publication'}",
        )
