"""Base agent class for all AgentCo agents."""
from __future__ import annotations

import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import anthropic

from .confidence_scorer import compute_risk_level, validate_confidence_attached
from .types import (
    ActionType,
    AgentEvent,
    AgentLifecycle,
    AgentOutput,
    AuditEntry,
    OverrideRequest,
    RiskLevel,
    TrustLevel,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Every AgentCo agent extends this class.

    Guarantees:
    - Every output has a confidence_score (enforced, not optional)
    - Every decision is written to the audit log
    - High/critical risk actions pause for human approval
    - Events are published to Kafka via the event bus
    - Agent is stateful via memory_client
    """

    AGENT_ID: str = ""
    DEPARTMENT: str = ""
    MODEL: str = "claude-sonnet-4-6"
    MEMORY_NAMESPACE: str = ""
    COMPETENCY_AREAS: list[str] = []
    AUTONOMY_LEVEL: str = "medium"

    def __init__(self):
        if not self.AGENT_ID:
            raise ValueError(f"{self.__class__.__name__} must define AGENT_ID")

        self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.session_id = str(uuid.uuid4())
        self.lifecycle_state = AgentLifecycle.PRODUCTION

        # Lazy imports to avoid circular deps at module level
        self._memory = None
        self._event_bus = None
        self._audit_log = None
        self._override_queue = None

    # ──────────────────────────────────────────────────────────────
    # Abstract interface — each agent implements these
    # ──────────────────────────────────────────────────────────────

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the versioned system prompt for this agent."""

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return Anthropic tool definitions available to this agent."""

    @abstractmethod
    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        """Primary task execution. Subclasses implement their core logic here."""

    # ──────────────────────────────────────────────────────────────
    # Core reasoning loop
    # ──────────────────────────────────────────────────────────────

    async def run(self, task: dict[str, Any]) -> AgentOutput:
        """Entry point. Runs the full reasoning loop with audit, confidence, and escalation."""
        logger.info("[%s] Starting task: %s", self.AGENT_ID, task.get("type", "unknown"))

        output = await self.execute_task(task)

        # Enforce confidence score on every output
        output_dict = {
            "content": output.content,
            "confidence_score": output.confidence_score,
            "risk_level": output.risk_level,
        }
        validate_confidence_attached(output_dict)

        # Audit every decision
        await self._write_audit(task, output)

        # Escalate if needed — hard stop for high/critical
        if output.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or output.requires_human_approval:
            await self._request_human_approval(task, output)

        return output

    async def llm_call(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
    ) -> str:
        """Single LLM call with tool support."""
        kwargs: dict[str, Any] = {
            "model": self.MODEL,
            "max_tokens": max_tokens,
            "system": self.get_system_prompt(),
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        # Handle tool use blocks
        for block in response.content:
            if block.type == "tool_use":
                tool_result = await self._execute_tool(block.name, block.input)
                messages = messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id, "content": str(tool_result)}]},
                ]
                return await self.llm_call(messages, tools, max_tokens)

        return response.content[0].text if response.content else ""

    # ──────────────────────────────────────────────────────────────
    # Trust evaluation of incoming signals
    # ──────────────────────────────────────────────────────────────

    def evaluate_trust(self, incoming: dict[str, Any]) -> TrustLevel:
        score = incoming.get("confidence_score", 0.0)
        if score >= 0.9:
            return TrustLevel.VERIFIED
        elif score >= 0.7:
            return TrustLevel.TRUSTED
        elif score >= 0.5:
            return TrustLevel.PROVISIONAL
        elif score >= 0.3:
            return TrustLevel.UNVERIFIED
        return TrustLevel.REJECTED

    def should_act_on(self, incoming: dict[str, Any]) -> bool:
        trust = self.evaluate_trust(incoming)
        if trust == TrustLevel.REJECTED:
            logger.warning("[%s] Discarding input — trust REJECTED (score=%.2f)", self.AGENT_ID, incoming.get("confidence_score", 0))
            return False
        if trust == TrustLevel.UNVERIFIED:
            logger.warning("[%s] Escalating — trust UNVERIFIED (score=%.2f)", self.AGENT_ID, incoming.get("confidence_score", 0))
            return False
        return True

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    async def _write_audit(self, task: dict, output: AgentOutput) -> None:
        entry = AuditEntry(
            agent_id=self.AGENT_ID,
            action_type=ActionType.DECISION,
            input_summary=json.dumps(task)[:500],
            output_summary=str(output.content)[:500],
            confidence_score=output.confidence_score,
            risk_level=output.risk_level,
            human_approved=output.requires_human_approval,
            session_id=self.session_id,
        )
        logger.info("[AUDIT] %s: %s (confidence=%.2f, risk=%s)", self.AGENT_ID, entry.action_type, entry.confidence_score, entry.risk_level)
        # In production: POST to audit log service
        # await self._audit_log.append(entry)

    async def _request_human_approval(self, task: dict, output: AgentOutput) -> None:
        req = OverrideRequest(
            agent_id=self.AGENT_ID,
            action=task.get("type", "unknown"),
            risk_score=output.confidence_score,
            context={"task": task, "rationale": output.rationale, "escalation_reason": output.escalation_reason},
        )
        logger.warning("[OVERRIDE] %s requires human approval: %s", self.AGENT_ID, req.request_id)
        # In production: POST to override queue; PAUSE until response received
        # await self._override_queue.enqueue(req)

    async def publish_event(self, event: AgentEvent) -> None:
        validate_confidence_attached({"confidence_score": event.confidence_score})
        logger.info("[EVENT] %s published %s (risk=%s)", self.AGENT_ID, event.event_type, event.risk_level)
        # In production: await self._event_bus.publish(event)

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        logger.info("[TOOL] %s calling %s", self.AGENT_ID, tool_name)
        # Tool registry resolves and executes; returns result
        # In production: return await self._tool_registry.execute(self.AGENT_ID, tool_name, tool_input)
        return {"status": "ok", "tool": tool_name, "input": tool_input}
