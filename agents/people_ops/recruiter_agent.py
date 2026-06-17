"""Recruiter-Agent — model benchmarking and upgrade proposals. No production access. Human approval required."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class RecruiterAgent(BaseAgent):
    AGENT_ID = "recruiter-agent"
    DEPARTMENT = "people_ops"
    MEMORY_NAMESPACE = "people_ops/recruiter"
    COMPETENCY_AREAS = ["model_benchmarking", "eval_running", "upgrade_proposals"]

    # HARD RULE: staging only — no production system access
    HAS_PRODUCTION_ACCESS = False

    def get_system_prompt(self) -> str:
        with open("agents/prompts/people_ops/recruiter_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        if task.get("environment") == "production":
            return AgentOutput(content={"blocked": True, "reason": "Recruiter-Agent has no production access — staging only"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="HARD CONSTRAINT: No production access")

        task_type = task.get("type", "benchmark")
        messages = [{"role": "user", "content": f"Recruiter task: {task_type}\nEnvironment: STAGING ONLY\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())

        return AgentOutput(
            content={"proposal": response, "status": "pending_human_approval", "note": "No agent upgrade or retirement goes live without explicit human approval — no exceptions"},
            confidence_score=0.87,
            risk_level=RiskLevel.HIGH,
            rationale=f"Upgrade proposal generated — requires human approval before any production deployment",
            requires_human_approval=True,
            escalation_reason="Agent upgrade/retirement requires explicit human approval",
        )
