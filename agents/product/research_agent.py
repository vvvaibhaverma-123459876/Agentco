"""Research-Agent — EVERY output MUST have a confidence score. Non-negotiable."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.confidence_scorer import score_output
from core.types import AgentEvent, AgentOutput, RiskLevel


class ResearchAgent(BaseAgent):
    AGENT_ID = "research-agent"
    DEPARTMENT = "product"
    MEMORY_NAMESPACE = "product/research"
    COMPETENCY_AREAS = ["user_research", "competitor_analysis", "market_signals", "survey_analysis"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/product/research_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "")
        if task_type == "user_interview_synthesis":
            return await self._synthesise_interviews(task)
        elif task_type == "competitor_monitoring":
            return await self._monitor_competitors(task)
        elif task_type == "market_signal":
            return await self._detect_market_signal(task)
        elif task_type == "survey_analysis":
            return await self._analyse_survey(task)
        else:
            return await self._generate_insight_report(task)

    async def _synthesise_interviews(self, task: dict) -> AgentOutput:
        transcripts = task.get("transcripts", [])
        messages = [{"role": "user", "content": f"Synthesise {len(transcripts)} user interview transcripts. Extract patterns, pain points, and key themes. Evaluate your evidence quality carefully.\n\nTranscripts: {transcripts[:3]}"}]
        response = await self.llm_call(messages, self.get_tools())

        # Confidence depends on sample size and source quality
        evidence = [t for t in transcripts if t]
        confidence = score_output(response, evidence, "user_interview_synthesis", self.COMPETENCY_AREAS)
        confidence = min(confidence, 0.85)  # Cap at 0.85 — interviews are qualitative

        return self._wrap_with_confidence(response, confidence, "user_interview_synthesis")

    async def _monitor_competitors(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Analyse competitor changes and positioning. Assess confidence based on data recency and source reliability.\n\nData: {task.get('competitor_data', {})}"}]
        response = await self.llm_call(messages, self.get_tools())
        data_sources = task.get("data_sources", [])
        confidence = score_output(response, data_sources, "competitor_analysis", self.COMPETENCY_AREAS)
        return self._wrap_with_confidence(response, confidence, "competitor_monitoring")

    async def _detect_market_signal(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Identify and assess market signals. Be explicit about evidence strength.\n\nSignals: {task.get('signals', [])}"}]
        response = await self.llm_call(messages)
        signals = task.get("signals", [])
        confidence = score_output(response, signals, "market_signal_detection", self.COMPETENCY_AREAS)
        confidence = min(confidence, 0.75)  # Market signals are inherently uncertain
        return self._wrap_with_confidence(response, confidence, "market_signal_detection")

    async def _analyse_survey(self, task: dict) -> AgentOutput:
        responses = task.get("responses", [])
        n = len(responses)
        messages = [{"role": "user", "content": f"Analyse survey with {n} responses. Apply statistical rigour. Note: n={n} affects confidence.\n\nData: {responses[:100]}"}]
        response = await self.llm_call(messages)
        # Statistical confidence: more responses = higher confidence, capped at 0.90
        confidence = min(0.40 + (n / 1000) * 0.50, 0.90)
        return self._wrap_with_confidence(response, confidence, f"survey_analysis_n{n}")

    async def _generate_insight_report(self, task: dict) -> AgentOutput:
        messages = [{"role": "user", "content": f"Generate insight report. Attach explicit confidence assessment.\n\nContext: {task}"}]
        response = await self.llm_call(messages, self.get_tools())
        evidence = task.get("evidence", [])
        confidence = score_output(response, evidence, "insight_generation", self.COMPETENCY_AREAS)

        output = self._wrap_with_confidence(response, confidence, "insight_report")

        # Publish insight to event bus
        await self.publish_event(AgentEvent(
            event_type="research.insight.published",
            producer_agent_id=self.AGENT_ID,
            confidence_score=confidence,
            payload={"insight_id": task.get("insight_id", ""), "confidence_score": confidence, "tags": task.get("tags", []), "summary": str(response)[:200]},
            risk_level=output.risk_level,
            requires_ack=False,
        ))
        return output

    def _wrap_with_confidence(self, content: Any, confidence: float, task_label: str) -> AgentOutput:
        """
        CRITICAL: Research-Agent ALWAYS attaches confidence score.
        Scores below 0.7 are flagged as unverified hypotheses.
        """
        if confidence < 0.5:
            risk = RiskLevel.HIGH
        elif confidence < 0.7:
            risk = RiskLevel.MEDIUM
        else:
            risk = RiskLevel.LOW

        is_low_confidence = confidence < 0.7
        return AgentOutput(
            content={"insight": content, "confidence_score": confidence, "task": task_label, "is_verified": confidence >= 0.7, "downstream_note": "UNVERIFIED HYPOTHESIS — do not treat as confirmed fact" if is_low_confidence else None},
            confidence_score=confidence,
            risk_level=risk,
            rationale=f"Research output for {task_label} — confidence {confidence:.2f}{'  (below 0.7 threshold)' if is_low_confidence else ''}",
        )
