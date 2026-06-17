"""A/B-Agent — experiment design, statistical analysis, recommendations (never acts unilaterally)."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class ABAgent(BaseAgent):
    AGENT_ID = "ab-agent"
    DEPARTMENT = "design"
    MEMORY_NAMESPACE = "design/ab"
    COMPETENCY_AREAS = ["experiment_design", "statistical_analysis", "recommendations"]

    # HARD RULE: never acts on results unilaterally
    CAN_IMPLEMENT_CHANGES = False

    def get_system_prompt(self) -> str:
        with open("agents/prompts/design/ab_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "implement":
            return AgentOutput(content={"blocked": True, "reason": "A/B-Agent produces recommendations only — never acts on results unilaterally"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="HARD CONSTRAINT: A/B-Agent cannot implement changes")

        messages = [{"role": "user", "content": f"A/B task: {task_type}. Apply statistical rigour (p < 0.05 minimum).\nData: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content={"recommendation": response, "action_required": "human_or_authorized_agent_must_implement"}, confidence_score=0.87, risk_level=RiskLevel.LOW, rationale=f"Statistical analysis complete — recommendation only")
