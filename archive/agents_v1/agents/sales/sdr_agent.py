"""SDR-Agent — prospect identification, outreach sequences, lead qualification."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class SDRAgent(BaseAgent):
    AGENT_ID = "sdr-agent"
    DEPARTMENT = "sales"
    MEMORY_NAMESPACE = "sales/sdr"
    COMPETENCY_AREAS = ["prospecting", "outreach", "qualification", "crm"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/sales/sdr_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "qualify_lead":
            lead = task.get("lead", {})
            messages = [{"role": "user", "content": f"Qualify lead using BANT framework.\n\nLead: {lead}"}]
            response = await self.llm_call(messages, self.get_tools())
            qualified = task.get("bant_score", 0) >= 70
            if qualified:
                await self.publish_event(AgentEvent(event_type="sales.lead.qualified", producer_agent_id=self.AGENT_ID, confidence_score=0.88, payload={"lead_id": lead.get("id"), "score": task.get("bant_score"), "company_size": lead.get("company_size"), "intent_signals": lead.get("intent_signals", [])}, risk_level=RiskLevel.LOW, requires_ack=False))
            return AgentOutput(content={"qualified": qualified, "assessment": response}, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale="BANT qualification complete")
        else:
            messages = [{"role": "user", "content": str(task)}]
            response = await self.llm_call(messages)
            return AgentOutput(content=response, confidence_score=0.82, risk_level=RiskLevel.LOW, rationale="SDR task")
