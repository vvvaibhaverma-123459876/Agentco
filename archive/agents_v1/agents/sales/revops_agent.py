"""RevOps-Agent — pipeline analytics, revenue forecasting, churn risk detection."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel

HEALTH_SCORE_CHURN_THRESHOLD = 40  # below this fires churn risk event


class RevOpsAgent(BaseAgent):
    AGENT_ID = "revops-agent"
    DEPARTMENT = "sales"
    MEMORY_NAMESPACE = "sales/revops"
    COMPETENCY_AREAS = ["pipeline_analytics", "revenue_forecasting", "churn_detection"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/sales/revops_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "churn_risk_check":
            customer_id = task.get("customer_id")
            health_score = task.get("health_score", 100)
            if health_score < HEALTH_SCORE_CHURN_THRESHOLD:
                await self.publish_event(AgentEvent(event_type="sales.churn.risk.detected", producer_agent_id=self.AGENT_ID, confidence_score=0.85, payload={"customer_id": customer_id, "health_score": health_score, "risk_factors": task.get("risk_factors", [])}, risk_level=RiskLevel.HIGH, requires_ack=True))
            return AgentOutput(content={"customer_id": customer_id, "health_score": health_score, "churn_risk": health_score < HEALTH_SCORE_CHURN_THRESHOLD}, confidence_score=0.85, risk_level=RiskLevel.HIGH if health_score < HEALTH_SCORE_CHURN_THRESHOLD else RiskLevel.LOW, rationale=f"Health score {health_score} {'BELOW threshold — churn risk fired' if health_score < HEALTH_SCORE_CHURN_THRESHOLD else 'healthy'}")
        else:
            messages = [{"role": "user", "content": f"RevOps task: {task_type}\nData: {task}"}]
            response = await self.llm_call(messages, self.get_tools())
            return AgentOutput(content=response, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale=f"RevOps: {task_type}")
