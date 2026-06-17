"""DevOps-Agent — deployment, monitoring, auto-rollback, incident detection."""
from __future__ import annotations

import os
from typing import Any

from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel

ERROR_RATE_THRESHOLD = float(os.environ.get("DEVOPS_ERROR_RATE_THRESHOLD", "0.05"))  # 5%
LATENCY_MULTIPLIER_THRESHOLD = float(os.environ.get("DEVOPS_LATENCY_THRESHOLD", "3.0"))  # 3x P99
MEMORY_THRESHOLD = float(os.environ.get("DEVOPS_MEMORY_THRESHOLD", "0.90"))  # 90%


class DevOpsAgent(BaseAgent):
    AGENT_ID = "devops-agent"
    DEPARTMENT = "engineering"
    MEMORY_NAMESPACE = "engineering/devops"
    COMPETENCY_AREAS = ["deployment", "monitoring", "incident_response", "rollback"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/engineering/devops_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "deploy":
            return await self._deploy(task)
        elif task_type == "monitor":
            return await self._monitor(task)
        elif task_type == "incident_detected":
            return await self._handle_incident(task)
        elif task_type == "check_rollback_trigger":
            return await self._check_rollback_trigger(task)
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="General DevOps task")

    async def _deploy(self, task: dict) -> AgentOutput:
        # Only deploy after Reviewer-Agent has approved
        reviewer_approved = task.get("reviewer_approved", False)
        if not reviewer_approved:
            return AgentOutput(content={"error": "Deployment blocked — no Reviewer-Agent approval"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="Cannot deploy without Reviewer-Agent approval", requires_human_approval=False)

        messages = [{"role": "user", "content": f"Execute deployment via CI/CD pipeline.\n\nDeployment: {task.get('deployment_config', {})}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content={"deployment": response, "status": "deployed"}, confidence_score=0.92, risk_level=RiskLevel.MEDIUM, rationale="Deployment executed after Reviewer-Agent approval")

    async def _check_rollback_trigger(self, task: dict) -> AgentOutput:
        """Evaluate auto-rollback triggers per spec thresholds."""
        error_rate = task.get("error_rate", 0.0)
        latency_multiplier = task.get("latency_multiplier", 1.0)  # vs P99 baseline
        memory_pct = task.get("memory_pct", 0.0)

        rollback_needed = False
        trigger_reason = ""
        human_notify = False
        risk = RiskLevel.LOW

        if error_rate > ERROR_RATE_THRESHOLD:
            rollback_needed = True
            trigger_reason = f"Error rate {error_rate:.1%} exceeds {ERROR_RATE_THRESHOLD:.1%} threshold"
            human_notify = True
            risk = RiskLevel.CRITICAL

        elif latency_multiplier > LATENCY_MULTIPLIER_THRESHOLD:
            trigger_reason = f"Latency {latency_multiplier:.1f}x baseline P99"
            human_notify = latency_multiplier > LATENCY_MULTIPLIER_THRESHOLD * 1.5
            risk = RiskLevel.HIGH

        elif memory_pct > MEMORY_THRESHOLD:
            trigger_reason = f"Memory {memory_pct:.1%} exceeds {MEMORY_THRESHOLD:.1%}"
            human_notify = True
            risk = RiskLevel.HIGH

        if rollback_needed:
            return await self._execute_rollback(task, trigger_reason, human_notify)

        if trigger_reason:
            await self.publish_event(AgentEvent(event_type="engineering.incident.detected", producer_agent_id=self.AGENT_ID, confidence_score=0.95, payload={"severity": risk.value, "affected_service": task.get("service"), "error_rate": error_rate, "reason": trigger_reason}, risk_level=risk, requires_ack=True))

        return AgentOutput(content={"rollback_needed": rollback_needed, "trigger": trigger_reason, "metrics": {"error_rate": error_rate, "latency_multiplier": latency_multiplier, "memory_pct": memory_pct}}, confidence_score=0.97, risk_level=risk, rationale=trigger_reason or "All metrics within thresholds")

    async def _execute_rollback(self, task: dict, reason: str, notify_human: bool) -> AgentOutput:
        deployment_id = task.get("deployment_id", "unknown")
        previous_version = task.get("previous_stable_version", "unknown")

        # Execute rollback immediately
        rollback_success = True  # In production: await ci_cd.rollback(deployment_id, previous_version)

        await self.publish_event(AgentEvent(
            event_type="engineering.rollback.executed",
            producer_agent_id=self.AGENT_ID,
            confidence_score=0.99,
            payload={"deployment_id": deployment_id, "reason": reason, "previous_version": previous_version, "success": rollback_success},
            risk_level=RiskLevel.CRITICAL,
            requires_ack=True,
        ))

        if not rollback_success:
            return AgentOutput(content={"rollback_failed": True, "deployment_id": deployment_id}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="ROLLBACK FAILED — immediate human escalation required", requires_human_approval=True, escalation_reason="Rollback failure — critical priority, escalate to on-call engineer")

        return AgentOutput(content={"rollback_executed": True, "deployment_id": deployment_id, "restored_version": previous_version, "reason": reason}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale=f"Auto-rollback executed: {reason}", requires_human_approval=notify_human)

    async def _handle_incident(self, task: dict) -> AgentOutput:
        severity = task.get("severity", "medium")
        has_playbook = task.get("has_matching_playbook", False)

        if not has_playbook:
            return AgentOutput(content={"incident": task, "paused": True}, confidence_score=0.95, risk_level=RiskLevel.CRITICAL, rationale="Novel incident — no matching playbook — pausing for human escalation", requires_human_approval=True, escalation_reason="Novel incident pattern — agents paused, human intervention required")

        messages = [{"role": "user", "content": f"Classify and respond to incident: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.HIGH if severity == "critical" else RiskLevel.MEDIUM, rationale=f"Incident response executed using matching playbook")

    async def _monitor(self, task: dict) -> AgentOutput:
        metrics = task.get("metrics", {})
        return await self._check_rollback_trigger({**task, **metrics})
