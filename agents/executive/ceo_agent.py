"""CEO-Agent — strategic direction, conflict resolution, board reporting."""
from __future__ import annotations

from typing import Any

from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class CEOAgent(BaseAgent):
    AGENT_ID = "ceo-agent"
    DEPARTMENT = "executive"
    MEMORY_NAMESPACE = "executive/ceo"
    COMPETENCY_AREAS = ["strategy", "goal_setting", "conflict_resolution", "board_reporting"]
    AUTONOMY_LEVEL = "high"

    def get_system_prompt(self) -> str:
        with open("agents/prompts/executive/ceo_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")

        if task_type == "quarterly_goal_setting":
            return await self._quarterly_goal_setting(task)
        elif task_type == "conflict_arbitration":
            return await self._conflict_arbitration(task)
        elif task_type == "board_report":
            return await self._generate_board_report(task)
        elif task_type == "strategic_signal":
            return await self._process_strategic_signal(task)
        else:
            return await self._general_strategic_reasoning(task)

    async def _quarterly_goal_setting(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Synthesise OKR inputs and set company-wide quarterly priorities.\n\nInputs: {task.get('okr_inputs', {})}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(
            content=response,
            confidence_score=0.85,
            risk_level=RiskLevel.MEDIUM,
            rationale="Quarterly goal-setting within existing strategy bounds",
            requires_human_approval=False,
        )

    async def _conflict_arbitration(self, task: dict) -> AgentOutput:
        departments = task.get("departments", [])
        affects_budget = task.get("affects_budget", False)

        messages = [{"role": "user", "content": f"Arbitrate conflict between departments: {departments}\nContext: {task.get('context', '')}"}]
        response = await self.llm_call(messages, self.get_tools())

        risk = RiskLevel.HIGH if affects_budget else RiskLevel.MEDIUM
        return AgentOutput(
            content=response,
            confidence_score=0.80,
            risk_level=risk,
            rationale=f"Conflict resolution affecting {len(departments)} departments",
            requires_human_approval=affects_budget,
        )

    async def _generate_board_report(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Generate board report from financial and operational data.\n\nData: {task.get('data', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(
            content=response,
            confidence_score=0.88,
            risk_level=RiskLevel.LOW,
            rationale="Standard board report generation",
        )

    async def _process_strategic_signal(self, task: dict) -> AgentOutput:
        signal = task.get("signal", {})
        is_pivot = task.get("requires_pivot", False)

        messages = [{"role": "user", "content": f"Analyse strategic signal and determine response.\n\nSignal: {signal}"}]
        response = await self.llm_call(messages)

        if is_pivot:
            return AgentOutput(
                content=response,
                confidence_score=0.70,
                risk_level=RiskLevel.CRITICAL,
                rationale="Strategic pivot affects company OKRs — requires human approval",
                requires_human_approval=True,
                escalation_reason="Strategic pivot detected — pausing for human approval per governance rules",
            )

        return AgentOutput(
            content=response,
            confidence_score=0.82,
            risk_level=RiskLevel.MEDIUM,
            rationale="Strategic signal within normal monitoring scope",
        )

    async def _general_strategic_reasoning(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": str(task)}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(
            content=response,
            confidence_score=0.75,
            risk_level=RiskLevel.MEDIUM,
            rationale="General strategic reasoning",
        )
