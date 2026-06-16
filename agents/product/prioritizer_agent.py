"""Prioritizer-Agent — owns the single ranked product priority list."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class PrioritizerAgent(BaseAgent):
    AGENT_ID = "prioritizer-agent"
    DEPARTMENT = "product"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "product/prioritizer"
    COMPETENCY_AREAS = ["feature_scoring", "priority_management", "trade_off_analysis"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/product/prioritizer_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "score_feature":
            return await self._score_feature(task)
        elif task_type == "reorder_priorities":
            return await self._reorder_priorities(task)
        elif task_type == "capacity_conflict":
            return await self._resolve_capacity_conflict(task)
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.80, risk_level=RiskLevel.LOW, rationale="General prioritization task")

    async def _score_feature(self, task: dict) -> AgentOutput:
        feature = task.get("feature", {})
        messages = [{"role": "user", "content": f"Score this feature against impact, effort, strategic alignment, and risk.\n\nFeature: {feature}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content={"score": response, "feature_id": feature.get("id")}, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="Feature scored with weighted model")

    async def _reorder_priorities(self, task: dict) -> AgentOutput:
        previous = task.get("previous_top3", [])
        new_top3 = task.get("proposed_top3", [])
        messages = [{"role": "user", "content": f"Validate and confirm priority reordering.\nPrevious: {previous}\nProposed: {new_top3}\nRationale: {task.get('rationale', '')}"}]
        response = await self.llm_call(messages, self.get_tools())

        await self.publish_event(AgentEvent(
            event_type="product.priority.changed",
            producer_agent_id=self.AGENT_ID,
            confidence_score=0.90,
            payload={"previous_top3": previous, "new_top3": new_top3, "rationale": response},
            risk_level=RiskLevel.MEDIUM,
            requires_ack=True,
        ))
        return AgentOutput(content={"new_priority_stack": new_top3, "rationale": response}, confidence_score=0.90, risk_level=RiskLevel.MEDIUM, rationale="Priority stack reordered")

    async def _resolve_capacity_conflict(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Engineering capacity cannot support current priority stack. Model trade-offs explicitly.\n\nContext: {task}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.82, risk_level=RiskLevel.MEDIUM, rationale="Capacity conflict trade-off analysis")
