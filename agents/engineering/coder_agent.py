"""Coder-Agent — feature implementation, bug fixing, unit tests. Never merges own PRs."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class CoderAgent(BaseAgent):
    AGENT_ID = "coder-agent"
    DEPARTMENT = "engineering"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "engineering/coder"
    COMPETENCY_AREAS = ["feature_implementation", "bug_fixing", "unit_testing", "refactoring"]

    # HARD RULE: Coder-Agent never merges. This is enforced here, not just in the prompt.
    CAN_MERGE = False

    def get_system_prompt(self) -> str:
        with open("agents/prompts/engineering/coder_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")

        # HARD RULE: Never change scope without PM-Agent
        if task.get("scope_change_requested") and not task.get("pm_agent_approved_scope_change"):
            return AgentOutput(content={"blocked": True, "reason": "Scope change requires PM-Agent approval — returning to spec"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Scope is law — PM-Agent must approve changes")

        if task_type == "implement_feature":
            return await self._implement_feature(task)
        elif task_type == "fix_bug":
            return await self._fix_bug(task)
        elif task_type == "refactor":
            return await self._refactor(task)
        elif task_type == "merge":
            # HARD RULE: Never
            return AgentOutput(content={"error": "Coder-Agent is not authorized to merge PRs — submit to Reviewer-Agent"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="HARD CONSTRAINT: Coder-Agent cannot merge own PRs")
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.80, risk_level=RiskLevel.LOW, rationale="General coding task")

    async def _implement_feature(self, task: dict) -> AgentOutput:
        spec = task.get("spec", {})
        arch_design = task.get("architect_design", {})

        if not spec:
            return AgentOutput(content={"blocked": True, "reason": "No spec provided — cannot implement without PM-Agent spec"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Spec required before implementation")

        messages = [{"role": "user", "content": f"Implement feature from spec. Write production code AND unit tests.\n\nSpec: {spec}\nArchitecture: {arch_design}"}]
        response = await self.llm_call(messages, self.get_tools())

        return AgentOutput(content={"implementation": response, "pr_status": "ready_for_review", "note": "Submitted to Reviewer-Agent — awaiting approval"}, confidence_score=0.82, risk_level=RiskLevel.MEDIUM, rationale="Feature implemented per spec — submitted for review")

    async def _fix_bug(self, task: dict) -> AgentOutput:
        bug = task.get("bug", {})
        # Check if it's a security vulnerability
        if bug.get("is_security_vulnerability"):
            await self.publish_event(AgentEvent(event_type="engineering.incident.detected", producer_agent_id=self.AGENT_ID, confidence_score=0.95, payload={"severity": "critical", "bug_id": bug.get("id"), "type": "security_vulnerability"}, risk_level=RiskLevel.CRITICAL, requires_ack=True))

        messages = [{"role": "user", "content": f"Fix bug with root cause analysis.\n\nBug: {bug}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content={"fix": response, "root_cause": "included_in_fix", "pr_status": "ready_for_review"}, confidence_score=0.85, risk_level=RiskLevel.MEDIUM, rationale="Bug fix with root cause analysis — submitted for review")

    async def _refactor(self, task: dict) -> AgentOutput:
        if not task.get("architect_approved_plan"):
            return AgentOutput(content={"blocked": True, "reason": "Refactoring requires Architect-Agent approved tech debt plan"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Refactoring only within Architect-Agent approved plans")

        messages = [{"role": "user", "content": f"Refactor code per approved tech debt plan.\n\nPlan: {task.get('plan', {})}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="Refactoring within approved plan")
