"""COO-Agent — cross-team orchestration, OKR tracking, dependency resolution."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class COOAgent(BaseAgent):
    AGENT_ID = "coo-agent"
    DEPARTMENT = "executive"
    MEMORY_NAMESPACE = "executive/coo"
    COMPETENCY_AREAS = ["orchestration", "okr_tracking", "dependency_resolution", "capacity_monitoring"]
    AUTONOMY_LEVEL = "high"

    def get_system_prompt(self) -> str:
        with open("agents/prompts/executive/coo_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "okr_tracking":
            return await self._track_okrs(task)
        elif task_type == "dependency_resolution":
            return await self._resolve_dependency(task)
        elif task_type == "bottleneck_detection":
            return await self._detect_bottleneck(task)
        elif task_type == "workflow_orchestration":
            return await self._orchestrate_workflow(task)
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content=response, confidence_score=0.82, risk_level=RiskLevel.LOW, rationale="Operational coordination task")

    async def _track_okrs(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Analyse OKR progress and identify at-risk goals.\n\nOKR data: {task.get('okr_data', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.90, risk_level=RiskLevel.LOW, rationale="OKR tracking within normal scope")

    async def _resolve_dependency(self, task: dict) -> AgentOutput:
        blocking_dept = task.get("blocking_department", "")
        affected_dept = task.get("affected_department", "")
        structural_change = task.get("requires_structural_change", False)

        messages = [{"role": "user", "content": f"Resolve dependency: {blocking_dept} is blocking {affected_dept}.\nContext: {task.get('context', '')}"}]
        response = await self.llm_call(messages)

        if structural_change:
            return AgentOutput(content=response, confidence_score=0.75, risk_level=RiskLevel.HIGH, rationale="Structural workflow change requires CEO-Agent approval", requires_human_approval=False, escalation_reason="Route to CEO-Agent for structural change approval")

        return AgentOutput(content=response, confidence_score=0.87, risk_level=RiskLevel.MEDIUM, rationale="Dependency resolved through coordination")

    async def _detect_bottleneck(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Identify workflow bottlenecks before they compound.\n\nData: {task.get('workflow_data', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="Bottleneck detection and early intervention")

    async def _orchestrate_workflow(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Orchestrate multi-department workflow: {task.get('workflow_name', '')}\nDepartments: {task.get('departments', [])}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale="Multi-department workflow coordination")
