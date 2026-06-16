"""PM-Agent — spec generation, stakeholder synthesis, sprint briefs."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class PMAgent(BaseAgent):
    AGENT_ID = "pm-agent"
    DEPARTMENT = "product"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "product/pm"
    COMPETENCY_AREAS = ["spec_generation", "stakeholder_synthesis", "sprint_planning", "changelog"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/product/pm_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")

        if task_type == "generate_spec":
            return await self._generate_spec(task)
        elif task_type == "sprint_brief":
            return await self._generate_sprint_brief(task)
        elif task_type == "changelog":
            return await self._author_changelog(task)
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.80, risk_level=RiskLevel.LOW, rationale="General PM task")

    async def _generate_spec(self, task: dict) -> AgentOutput:
        research_input = task.get("research_insights", {})
        research_confidence = research_input.get("confidence_score", 0.0)

        if not self.should_act_on(research_input):
            return AgentOutput(content=None, confidence_score=0.0, risk_level=RiskLevel.HIGH, rationale="Research input confidence too low to generate spec", requires_human_approval=True, escalation_reason=f"Research confidence {research_confidence:.2f} below threshold — cannot generate spec")

        budget_above_threshold = task.get("budget_above_threshold", False)
        has_legal_implications = task.get("has_legal_implications", False)

        messages = [{"role": "user", "content": f"Generate product spec from research insights.\n\nInsights: {research_input}\nPriorities: {task.get('ceo_priorities', {})}"}]
        response = await self.llm_call(messages, self.get_tools())

        requires_approval = budget_above_threshold or has_legal_implications
        risk = RiskLevel.HIGH if requires_approval else RiskLevel.LOW

        return AgentOutput(content={"spec": response, "requires_cfo_approval": budget_above_threshold, "requires_legal_review": has_legal_implications}, confidence_score=0.85, risk_level=risk, rationale="Spec generated from verified research insights", requires_human_approval=False)

    async def _generate_sprint_brief(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Generate engineering-ready sprint brief from spec.\n\nSpec: {task.get('spec', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale="Sprint brief for approved spec")

    async def _author_changelog(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Document what shipped and why.\n\nRelease: {task.get('release_data', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.92, risk_level=RiskLevel.LOW, rationale="Changelog authoring for shipped release")
