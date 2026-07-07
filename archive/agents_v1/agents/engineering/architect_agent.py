"""Architect-Agent — system design, ADRs, tech debt, standards enforcement."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class ArchitectAgent(BaseAgent):
    AGENT_ID = "architect-agent"
    DEPARTMENT = "engineering"
    MEMORY_NAMESPACE = "engineering/architect"
    COMPETENCY_AREAS = ["system_design", "adr", "tech_debt", "standards"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/engineering/architect_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "system_design":
            messages = [{"role": "user", "content": f"Design system architecture for: {task.get('spec', {})}. Include scalability modelling."}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.MEDIUM, rationale="System design with scalability modelling")
        elif task_type == "adr":
            messages = [{"role": "user", "content": f"Write Architecture Decision Record for: {task.get('decision', '')}"}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.90, risk_level=RiskLevel.LOW, rationale="ADR for significant technical decision")
        elif task_type == "tech_debt_assessment":
            messages = [{"role": "user", "content": f"Evaluate and score tech debt with business impact: {task.get('code_area', '')}"}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.82, risk_level=RiskLevel.LOW, rationale="Tech debt assessment with business impact")
        elif task_type == "design_review":
            messages = [{"role": "user", "content": f"Review implementation for architectural compliance.\n\nImplementation: {task.get('implementation', {})}"}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale="Architectural compliance review")
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.80, risk_level=RiskLevel.LOW, rationale="General architecture task")
