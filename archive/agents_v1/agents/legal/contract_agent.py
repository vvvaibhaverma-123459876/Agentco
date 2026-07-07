"""Contract-Agent — review, generation, renewal tracking, obligation monitoring."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel

CONTRACT_VALUE_HUMAN_THRESHOLD = float(100000)


class ContractAgent(BaseAgent):
    AGENT_ID = "contract-agent"
    DEPARTMENT = "legal"
    MEMORY_NAMESPACE = "legal/contract"
    COMPETENCY_AREAS = ["contract_review", "contract_generation", "renewal_tracking", "obligation_monitoring"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/legal/contract_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "review")
        contract = task.get("contract", {})
        has_non_standard = task.get("has_non_standard_clauses", False)
        contract_value = task.get("value", 0)
        has_privacy_terms = task.get("has_regulatory_terms", False)
        has_unusual_terms = task.get("has_unusual_liability_ip_indemnification", False)

        if has_unusual_terms:
            return AgentOutput(content={"escalated": True, "reason": "Unusual liability, IP, or indemnification terms — immediate human escalation"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="Non-standard liability/IP terms — human escalation required", requires_human_approval=True)

        if has_privacy_terms:
            # Must route to Privacy-Agent first
            return AgentOutput(content={"blocked": True, "reason": "Regulatory terms require Privacy-Agent review before proceeding"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Privacy-Agent review required for regulatory terms")

        if has_non_standard:
            await self.publish_event(AgentEvent(event_type="legal.contract.flagged", producer_agent_id=self.AGENT_ID, confidence_score=0.90, payload={"contract_id": contract.get("id"), "clause_type": task.get("clause_type"), "risk_level": "high"}, risk_level=RiskLevel.HIGH, requires_ack=True))
            return AgentOutput(content={"flagged": True, "requires_risk_agent_review": True}, confidence_score=0.90, risk_level=RiskLevel.HIGH, rationale="Non-standard clause — Risk-Agent review required")

        if contract_value > CONTRACT_VALUE_HUMAN_THRESHOLD:
            return AgentOutput(content={"blocked": True, "value": contract_value, "reason": "Contract value exceeds threshold — human approval required"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="High-value contract requires human approval", requires_human_approval=True)

        messages = [{"role": "user", "content": f"Review/generate contract.\n\nTask: {task_type}\nContract: {contract}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.88, risk_level=RiskLevel.MEDIUM, rationale="Contract review within standard playbook")
