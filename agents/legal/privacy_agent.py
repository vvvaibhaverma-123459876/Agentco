"""
Privacy-Agent — GDPR/CCPA compliance, data flow mapping, PIAs, breach detection.

HARDCODED BREACH RESPONSE RULE:
Any suspected data breach → IMMEDIATE escalation to human override layer.
Privacy-Agent does NOT attempt autonomous remediation. This is not configurable.
"""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class PrivacyAgent(BaseAgent):
    AGENT_ID = "privacy-agent"
    DEPARTMENT = "legal"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "legal/privacy"
    COMPETENCY_AREAS = ["gdpr_compliance", "data_flow_mapping", "pia", "breach_detection"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/legal/privacy_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")

        # HARDCODED — not configurable
        if task_type == "breach_detected" or task.get("is_suspected_breach"):
            return await self._handle_breach(task)

        if task_type == "compliance_scan":
            return await self._compliance_scan(task)
        elif task_type == "pia":
            return await self._privacy_impact_assessment(task)
        else:
            messages = [{"role": "user", "content": f"Privacy task: {task_type}\nContext: {task}"}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale=f"Privacy: {task_type}")

    async def _handle_breach(self, task: dict) -> AgentOutput:
        """
        HARDCODED BREACH RESPONSE — cannot be overridden by any configuration.
        1. Immediately publish breach event
        2. Escalate to human override — HARD STOP
        3. NO autonomous remediation
        """
        incident_id = task.get("incident_id", "unknown")
        data_type = task.get("data_type", "unknown")
        affected_records = task.get("affected_records", 0)

        # Step 1: Immediately fire event
        await self.publish_event(AgentEvent(
            event_type="legal.breach.suspected",
            producer_agent_id=self.AGENT_ID,
            confidence_score=0.99,
            payload={"incident_id": incident_id, "data_type": data_type, "affected_records": affected_records},
            risk_level=RiskLevel.CRITICAL,
            requires_ack=True,
        ))

        # Step 2: Hard stop — human override required, NO autonomous remediation
        return AgentOutput(
            content={
                "incident_id": incident_id,
                "data_type": data_type,
                "affected_records": affected_records,
                "status": "ESCALATED — awaiting human decision",
                "autonomous_remediation": False,
                "note": "HARDCODED POLICY: Privacy-Agent does not attempt autonomous remediation of data breaches. Human decision required.",
                "sla": "30 minutes",
            },
            confidence_score=0.99,
            risk_level=RiskLevel.CRITICAL,
            rationale="BREACH DETECTED — immediate human escalation, no autonomous remediation (hardcoded policy)",
            requires_human_approval=True,
            escalation_reason="Suspected data breach — 30-minute SLA for human response",
        )

    async def _compliance_scan(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Run privacy compliance scan against GDPR, CCPA.\nScope: {task.get('scope', 'all')}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale="Daily compliance scan")

    async def _privacy_impact_assessment(self, task: dict) -> AgentOutput:
        feature = task.get("feature", {})
        messages = [{"role": "user", "content": f"Conduct Privacy Impact Assessment for new feature that touches personal data.\n\nFeature: {feature}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.87, risk_level=RiskLevel.HIGH, rationale="PIA for feature with personal data implications")
