"""AE-Agent — discovery, proposals, deal negotiation. Hard limits on discounts and terms."""
from __future__ import annotations
import os
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel

MAX_DISCOUNT_PCT = float(os.environ.get("AE_MAX_DISCOUNT_PCT", "15"))
STRATEGIC_DEAL_THRESHOLD = float(os.environ.get("AE_STRATEGIC_DEAL_ARR", "100000"))


class AEAgent(BaseAgent):
    AGENT_ID = "ae-agent"
    DEPARTMENT = "sales"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "sales/ae"
    COMPETENCY_AREAS = ["discovery", "proposals", "negotiation", "deal_analysis"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/sales/ae_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        discount_pct = task.get("discount_pct", 0)
        arr = task.get("arr", 0)
        non_standard_terms = task.get("non_standard_terms", False)

        # HARD LIMITS
        if discount_pct > MAX_DISCOUNT_PCT:
            return AgentOutput(content={"blocked": True, "reason": f"Discount {discount_pct}% exceeds {MAX_DISCOUNT_PCT}% limit — requires CFO-Agent approval"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Discount above threshold — CFO approval required", requires_human_approval=False)

        if non_standard_terms:
            return AgentOutput(content={"blocked": True, "reason": "Non-standard terms require Contract-Agent and Legal review"}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale="Non-standard terms — legal review required")

        if arr >= STRATEGIC_DEAL_THRESHOLD:
            return AgentOutput(content={"routed_to_ceo": True, "arr": arr}, confidence_score=0.99, risk_level=RiskLevel.HIGH, rationale=f"Strategic deal ≥${STRATEGIC_DEAL_THRESHOLD:,.0f} — CEO-Agent involvement required", requires_human_approval=True)

        if task_type == "close_deal":
            await self.publish_event(AgentEvent(event_type="sales.deal.closed", producer_agent_id=self.AGENT_ID, confidence_score=0.95, payload={"deal_id": task.get("deal_id"), "arr": arr, "contract_term": task.get("contract_term"), "customer_id": task.get("customer_id")}, risk_level=RiskLevel.LOW, requires_ack=True))

        messages = [{"role": "user", "content": f"Sales task: {task_type}\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(content=response, confidence_score=0.87, risk_level=RiskLevel.LOW, rationale=f"AE task: {task_type}")
