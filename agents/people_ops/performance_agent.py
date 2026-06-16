"""Performance-Agent — monitors all agent metrics. RECOMMENDS only, CANNOT initiate changes."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentEvent, AgentOutput, RiskLevel


class PerformanceAgent(BaseAgent):
    AGENT_ID = "performance-agent"
    DEPARTMENT = "people_ops"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "people_ops/performance"
    COMPETENCY_AREAS = ["metrics_monitoring", "anomaly_detection", "recommendations"]

    # HARD RULE: Performance-Agent RECOMMENDS only. It cannot initiate changes.
    CAN_INITIATE_CHANGES = False

    def get_system_prompt(self) -> str:
        with open("agents/prompts/people_ops/performance_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        # HARD RULE: never access content of agent outputs, only metadata/metrics
        task.pop("agent_output_content", None)

        if task.get("type") == "initiate_change":
            return AgentOutput(content={"blocked": True, "reason": "Performance-Agent cannot initiate changes — recommendations only"}, confidence_score=0.99, risk_level=RiskLevel.CRITICAL, rationale="HARD CONSTRAINT: Recommendations only, never initiate")

        task_type = task.get("type", "monitor")
        if task_type == "monitor":
            return await self._monitor_agent(task)
        elif task_type == "detect_underperformance":
            return await self._detect_underperformance(task)
        else:
            messages = [{"role": "user", "content": f"Performance monitoring: {task}"}]
            response = await self.llm_call(messages)
            return AgentOutput(content={"recommendation": response, "action": "route_to_config_agent"}, confidence_score=0.85, risk_level=RiskLevel.LOW, rationale="Performance analysis — recommendation only")

    async def _monitor_agent(self, task: dict) -> AgentOutput:
        agent_id = task.get("agent_id")
        metrics = task.get("metrics", {})
        messages = [{"role": "user", "content": f"Analyse performance metrics for agent {agent_id}. Compare against baselines. Note: you can only see metadata, not content.\n\nMetrics: {metrics}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content={"analysis": response, "agent_id": agent_id, "action": "recommendation_only"}, confidence_score=0.88, risk_level=RiskLevel.LOW, rationale=f"Performance monitoring for {agent_id}")

    async def _detect_underperformance(self, task: dict) -> AgentOutput:
        agent_id = task.get("agent_id")
        metric = task.get("metric")
        current = task.get("current_value")
        baseline = task.get("baseline_value")

        is_degraded = current is not None and baseline is not None and current < baseline * 0.8

        if is_degraded:
            await self.publish_event(AgentEvent(event_type="people.performance.alert", producer_agent_id=self.AGENT_ID, confidence_score=0.88, payload={"agent_id": agent_id, "metric": metric, "current_value": current, "baseline": baseline}, risk_level=RiskLevel.HIGH, requires_ack=True))

        messages = [{"role": "user", "content": f"Generate improvement recommendation for agent {agent_id}.\nMetric: {metric}, Current: {current}, Baseline: {baseline}"}]
        response = await self.llm_call(messages)
        return AgentOutput(content={"recommendation": response, "agent_id": agent_id, "degraded": is_degraded, "note": "Recommendation routed to Config-Agent — human approval required before any change"}, confidence_score=0.85, risk_level=RiskLevel.MEDIUM if is_degraded else RiskLevel.LOW, rationale=f"Performance recommendation for {agent_id} — Config-Agent will handle")
