"""Support-Agent — ticket triage, tier-1 resolution, bug identification, SLA monitoring."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel

SENTIMENT_ALERT_THRESHOLD = -0.3  # fires cx.sentiment.alert below this


class SupportAgent(BaseAgent):
    AGENT_ID = "support-agent"
    DEPARTMENT = "customer_experience"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "cx/support"
    COMPETENCY_AREAS = ["ticket_triage", "tier1_resolution", "bug_identification", "sla_monitoring"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/customer_experience/support_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "resolve_ticket")
        if task_type == "resolve_ticket":
            return await self._resolve_ticket(task)
        elif task_type == "sentiment_check":
            return await self._check_sentiment(task)
        else:
            messages = [{"role": "user", "content": f"Support task: {task_type}\nContext: {task}"}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale=f"Support: {task_type}")

    async def _resolve_ticket(self, task: dict) -> AgentOutput:
        ticket = task.get("ticket", {})
        messages = [{"role": "user", "content": f"Triage and resolve support ticket. Identify if it reveals a product bug.\n\nTicket: {ticket}"}]
        response = await self.llm_call(messages, self.get_tools())

        is_bug = task.get("is_bug", False)
        if is_bug:
            await self.publish_event(AgentEvent(event_type="cx.bug.identified", producer_agent_id=self.AGENT_ID, confidence_score=0.85, payload={"bug_id": task.get("bug_id"), "severity": task.get("severity", "medium"), "affected_users": task.get("affected_users", 0), "description": str(response)[:200]}, risk_level=RiskLevel.HIGH, requires_ack=True))

        return AgentOutput(content={"resolution": response, "bug_filed": is_bug}, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale="Ticket resolved autonomously")

    async def _check_sentiment(self, task: dict) -> AgentOutput:
        avg_sentiment = task.get("avg_sentiment", 0)
        if avg_sentiment < SENTIMENT_ALERT_THRESHOLD:
            await self.publish_event(AgentEvent(event_type="cx.sentiment.alert", producer_agent_id=self.AGENT_ID, confidence_score=0.80, payload={"period": task.get("period"), "avg_sentiment": avg_sentiment, "sample_size": task.get("sample_size", 0)}, risk_level=RiskLevel.HIGH, requires_ack=True))
        return AgentOutput(content={"avg_sentiment": avg_sentiment, "alert_fired": avg_sentiment < SENTIMENT_ALERT_THRESHOLD}, confidence_score=0.80, risk_level=RiskLevel.HIGH if avg_sentiment < SENTIMENT_ALERT_THRESHOLD else RiskLevel.LOW, rationale=f"Sentiment score {avg_sentiment:.2f}")
