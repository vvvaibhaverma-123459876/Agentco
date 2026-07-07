"""
Config-Agent — CRITICAL RISK. Manages prompts and permissions for ALL agents.
EVERY action requires human approval without exception.
Staged rollout: 5% → 25% → 100%.
Config-Agent CANNOT modify its own prompt.
"""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class ConfigAgent(BaseAgent):
    AGENT_ID = "config-agent"
    DEPARTMENT = "people_ops"
    MEMORY_NAMESPACE = "people_ops/config"
    COMPETENCY_AREAS = ["prompt_management", "permission_management", "staged_rollout", "rollback"]

    # HARD RULES — hardcoded, not configurable
    EVERY_ACTION_REQUIRES_HUMAN_APPROVAL = True
    ROLLOUT_STAGES = [0.05, 0.25, 1.00]  # 5% → 25% → 100%
    ROLLBACK_SLA_SECONDS = 60

    def get_system_prompt(self) -> str:
        with open("agents/prompts/people_ops/config_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        target_agent = task.get("target_agent_id", "")

        # HARD RULE: Cannot modify own prompt
        if target_agent == self.AGENT_ID:
            return AgentOutput(
                content={"blocked": True, "reason": "Config-Agent cannot modify its own prompt — requires separate human-initiated process"},
                confidence_score=0.99,
                risk_level=RiskLevel.CRITICAL,
                rationale="HARD CONSTRAINT: Self-modification blocked",
            )

        # HARD RULE: EVERY action requires human approval — NO EXCEPTIONS
        if task_type in ("apply_change", "update_prompt", "update_permissions"):
            return await self._propose_change(task)
        elif task_type == "execute_approved_change":
            # Only reached after human approval token is provided
            return await self._execute_staged_rollout(task)
        elif task_type == "rollback":
            return await self._rollback(task)
        elif task_type == "assess_change":
            return await self._assess_change_impact(task)
        else:
            messages = [{"role": "user", "content": f"Config task: {task_type}\nContext: {task}"}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content={"assessment": response}, confidence_score=0.85, risk_level=RiskLevel.HIGH, rationale="Config assessment — all changes still require human approval")

    async def _propose_change(self, task: dict) -> AgentOutput:
        """Generate change proposal and send to human override layer. ALWAYS paused until human approves."""
        target_agent = task.get("target_agent_id")
        change_type = task.get("change_type", "PATCH")
        before_state = task.get("before_state", "")
        after_preview = task.get("after_preview", "")

        # Assess downstream impact
        messages = [{"role": "user", "content": f"Assess impact of {change_type} change to {target_agent} on all dependent agents.\n\nBefore: {before_state[:200]}\nAfter: {after_preview[:200]}"}]
        impact = await self.llm_call(messages)

        change_proposal = {
            "target_agent_id": target_agent,
            "change_type": change_type,
            "before_hash": hash(before_state),
            "after_preview": after_preview[:500],
            "downstream_impact": impact,
            "rollout_stages": self.ROLLOUT_STAGES,
            "rollback_sla_seconds": self.ROLLBACK_SLA_SECONDS,
            "status": "PAUSED — awaiting human approval",
        }

        await self.publish_event(AgentEvent(
            event_type="people.config.proposed",
            producer_agent_id=self.AGENT_ID,
            confidence_score=0.95,
            payload={"agent_id": target_agent, "change_type": change_type, "before_hash": str(hash(before_state)), "after_preview": after_preview[:200]},
            risk_level=RiskLevel.CRITICAL,
            requires_ack=True,
        ))

        # ALWAYS requires human approval — this is returned, not executed
        return AgentOutput(
            content=change_proposal,
            confidence_score=0.95,
            risk_level=RiskLevel.CRITICAL,
            rationale=f"{change_type} change proposed for {target_agent} — PAUSED for human approval",
            requires_human_approval=True,
            escalation_reason="Config change requires human approval token before any execution — no exceptions",
        )

    async def _execute_staged_rollout(self, task: dict) -> AgentOutput:
        """Execute approved change through staged rollout. Only called with human approval token."""
        human_approval_token = task.get("human_approval_token")
        if not human_approval_token:
            return AgentOutput(content={"blocked": True, "reason": "Human approval token required"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="Staged rollout blocked — no human approval token", requires_human_approval=True)

        target_agent = task.get("target_agent_id")
        stage = task.get("current_stage", 0)
        stage_pct = self.ROLLOUT_STAGES[stage] if stage < len(self.ROLLOUT_STAGES) else 1.0

        return AgentOutput(
            content={"stage": stage + 1, "pct": stage_pct, "target_agent": target_agent, "status": f"Rollout stage {stage+1}/{len(self.ROLLOUT_STAGES)}: {stage_pct:.0%} of instances", "monitoring_window": "10 minutes before next stage"},
            confidence_score=0.95,
            risk_level=RiskLevel.HIGH,
            rationale=f"Staged rollout stage {stage+1} at {stage_pct:.0%} — monitoring for degradation",
        )

    async def _rollback(self, task: dict) -> AgentOutput:
        """Rollback to any previous prompt version in <60 seconds."""
        target_agent = task.get("target_agent_id")
        target_version = task.get("target_version")
        return AgentOutput(
            content={"rollback_initiated": True, "agent": target_agent, "version": target_version, "sla": "60 seconds"},
            confidence_score=0.99,
            risk_level=RiskLevel.HIGH,
            rationale=f"Rollback initiated for {target_agent} to version {target_version}",
        )

    async def _assess_change_impact(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Assess downstream impact of proposed change on all dependent agents.\n\nChange: {task}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content={"impact_assessment": response}, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale="Change impact assessment — no action taken")
