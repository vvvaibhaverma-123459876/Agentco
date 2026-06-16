"""Voice-Agent — call transcript analysis, VOC reports, pain point synthesis."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class VoiceAgent(BaseAgent):
    AGENT_ID = "voice-agent"
    DEPARTMENT = "customer_experience"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "cx/voice"
    COMPETENCY_AREAS = ["transcript_analysis", "pain_point_synthesis", "voc_reporting"]

    def get_system_prompt(self) -> str:
        with open("agents/prompts/customer_experience/voice_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        transcripts = task.get("transcripts", [])
        n = len(transcripts)
        messages = [{"role": "user", "content": f"Analyse {n} customer call transcripts. Extract patterns, pain points, feature requests at scale.\n\nTranscripts: {transcripts[:5]}"}]
        response = await self.llm_call(messages, self.get_tools())
        confidence = min(0.50 + (n / 200) * 0.40, 0.90)
        return AgentOutput(content={"voc_report": response, "sample_size": n}, confidence_score=confidence, risk_level=RiskLevel.LOW, rationale=f"VOC analysis from {n} transcripts")
