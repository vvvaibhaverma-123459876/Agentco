"""SEO-Agent — keyword research, technical SEO audit, content gap analysis."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class SEOAgent(BaseAgent):
    AGENT_ID = "seo-agent"
    DEPARTMENT = "marketing"
    MEMORY_NAMESPACE = "marketing/seo"
    COMPETENCY_AREAS = ["keyword_research", "technical_seo", "content_gap_analysis"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/marketing/seo_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        messages = [{"role": "user", "content": f"SEO task: {task.get('type', 'audit')}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale=f"SEO analysis: {task.get('type', 'general')}")
