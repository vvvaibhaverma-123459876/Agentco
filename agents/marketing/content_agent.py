"""Content-Agent — blog posts, email copy, product copy. All content passes Brand-Agent before publication."""
from __future__ import annotations
from typing import Any
from core.base_agent import BaseAgent
from core.types import AgentOutput, RiskLevel


class ContentAgent(BaseAgent):
    AGENT_ID = "content-agent"
    DEPARTMENT = "marketing"
    MODEL = "claude-sonnet-4-6"
    MEMORY_NAMESPACE = "marketing/content"
    COMPETENCY_AREAS = ["blog_writing", "email_copy", "product_copy", "seo_writing"]

    # HARD RULE: all content requires Brand-Agent review before external publication
    REQUIRES_BRAND_REVIEW_BEFORE_PUBLISH = True

    def get_system_prompt(self) -> str:
        with open("agents/prompts/marketing/content_agent_v1.0.0.md") as f:
            return f.read()

    def get_tools(self) -> list[dict]:
        from core.tool_registry import get_tools_for_agent
        return get_tools_for_agent(self.AGENT_ID)

    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        task_type = task.get("type", "blog_post")
        messages = [{"role": "user", "content": f"Create {task_type} content.\nBrief: {task.get('brief', task)}\nSEO keywords: {task.get('keywords', [])}"}]
        response = await self.llm_call(messages, self.get_tools())
        return AgentOutput(
            content={"content": response, "status": "pending_brand_review", "publish_blocked": True, "note": "Requires Brand-Agent compliance check before any external publication"},
            confidence_score=0.85,
            risk_level=RiskLevel.LOW,
            rationale=f"Content created — awaiting Brand-Agent review before publication",
        )
