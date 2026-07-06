"""Base agent class for all AgentCo agents."""
from __future__ import annotations

import json
import logging
import os
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from runtime.base_agent.audit_writer import (
    AuditUnavailableError,
    AuditWriter,
    DurableAuditWriter,
)
from runtime.base_agent.llm_client import make_client
from runtime.base_agent.model_tiers import model_for
from .tools import register_all_tools

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


class GovernanceUnavailableError(RuntimeError):
    """Raised when V1 high/critical actions are disabled pending approval infrastructure."""


class BaseAgent(ABC):
    """
    Every AgentCo agent extends this class.

    Guarantees:
    - Every output has a confidence_score (enforced, not optional)
    - Every decision is written to the audit log
    - High/critical risk actions are disabled pending approval-resume infrastructure; use BaseAgentV2 for approval-gated execution
    - Events are published to Kafka via the event bus
    - Agent is stateful via memory_client
    """

    AGENT_ID: str = ""
    DEPARTMENT: str = ""
    # MODEL is resolved from the local model-tier map (model_for(AGENT_ID)) unless
    # a subclass overrides it. No cloud model ids are hardcoded anywhere.
    MODEL: str = ""
    MEMORY_NAMESPACE: str = ""
    COMPETENCY_AREAS: list[str] = []
    AUTONOMY_LEVEL: str = "medium"

    def __init__(self, audit_writer: Optional[AuditWriter] = None):
        if not self.AGENT_ID:
            raise ValueError(f"{self.__class__.__name__} must define AGENT_ID")

        # Local-first LLM client (Ollama / any OpenAI-compatible endpoint).
        # Model resolves from the tier map unless the subclass sets MODEL.
        self.client = make_client()
        self.model = self.MODEL or model_for(self.AGENT_ID)
        self.session_id = str(uuid.uuid4())
        # Register real tool handlers on first agent instantiation
        register_all_tools()
        self.lifecycle_state = AgentLifecycle.PRODUCTION

        # Lazy imports to avoid circular deps at module level
        self._memory = None
        self._event_bus = None
        self._audit_log = None
        self._override_queue = None
        self._audit_writer = audit_writer if audit_writer is not None else DurableAuditWriter.from_env()
        self._audit_failures = 0

    # ──────────────────────────────────────────────────────────────
    # Abstract interface — each agent implements these
    # ──────────────────────────────────────────────────────────────

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the versioned system prompt for this agent."""

    @abstractmethod
    def get_tools(self) -> list[dict]:
        """Return tool definitions (OpenAI-compatible schema) available to this agent."""

    @abstractmethod
    async def execute_task(self, task: dict[str, Any]) -> AgentOutput:
        """Primary task execution. Subclasses implement their core logic here."""

    # ──────────────────────────────────────────────────────────────
    # Core reasoning loop
    # ──────────────────────────────────────────────────────────────

    async def run(self, task: dict[str, Any]) -> AgentOutput:
        """Entry point. Low/medium actions may execute; high/critical V1 actions always raise after audit/override recording."""
        logger.info("[%s] Starting task: %s", self.AGENT_ID, task.get("type", "unknown"))

        output = await self.execute_task(task)

        # Enforce confidence score on every output
        output_dict = {
            "content": output.content,
            "confidence_score": output.confidence_score,
            "risk_level": output.risk_level,
        }
        validate_confidence_attached(output_dict)

        # Escalate if needed — hard stop for high/critical
        if output.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or output.requires_human_approval:
            await self._write_audit(task, output, require_ack=True)
            request_id = await self._request_human_approval(task, output, require_record=True)
            raise GovernanceUnavailableError(
                f"human approval required for {self.AGENT_ID}; override_request_id={request_id}"
            )

        # Audit low/medium decisions after validation; failures are visible but non-blocking.
        await self._write_audit(task, output, require_ack=False)

        return output

    async def llm_call(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
    ) -> str:
        """Single LLM call with tool support (OpenAI-compatible / Ollama)."""
        chat_messages = [{"role": "system", "content": self.get_system_prompt()}] + messages
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": chat_messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        # Handle tool calls (OpenAI-style)
        tool_calls = getattr(choice, "tool_calls", None)
        if tool_calls:
            follow_up = messages + [choice.model_dump()]
            for call in tool_calls:
                args = json.loads(call.function.arguments or "{}")
                tool_result = await self._execute_tool(call.function.name, args)
                follow_up.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(tool_result),
                })
            return await self.llm_call(follow_up, tools, max_tokens)

        return choice.content or ""

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

    async def _write_audit(self, task: dict, output: AgentOutput, *, require_ack: bool) -> None:
        logger.info("[AUDIT] %s: %s (confidence=%.2f, risk=%s)",
                    self.AGENT_ID, ActionType.DECISION, output.confidence_score, output.risk_level)
        if self._audit_writer is None:
            self._audit_failures += 1
            message = f"No audit writer configured for V1 agent={self.AGENT_ID}"
            if require_ack:
                raise GovernanceUnavailableError(message)
            logger.error("[AUDIT_FAILURE] %s: %s", self.AGENT_ID, message)
            return
        try:
            ack = self._audit_writer.write({
                "agent_id": self.AGENT_ID,
                "prompt_version": "v1",
                "action_type": ActionType.DECISION.value,
                "description": json.dumps(task)[:500],
                "stated_confidence": float(output.confidence_score),
                "trusted_confidence": float(output.confidence_score),
                "risk_level": output.risk_level.value if hasattr(output.risk_level, "value") else str(output.risk_level),
                "domain": self.DEPARTMENT or "general",
                "prediction_id": None,
                "override_id": None,
                "outcome": "blocked" if require_ack else "executed",
                "session_id": self.session_id,
            })
            if not ack or not ack.get("log_id"):
                raise AuditUnavailableError("audit writer returned no acknowledgement")
        except Exception as e:
            self._audit_failures += 1
            if require_ack:
                if isinstance(e, GovernanceUnavailableError):
                    raise
                raise GovernanceUnavailableError(f"audit unavailable for {self.AGENT_ID}: {e}") from e
            logger.error("[AUDIT_FAILURE] %s: %s", self.AGENT_ID, e)

    async def _request_human_approval(self, task: dict, output: AgentOutput, *, require_record: bool) -> str | None:
        from .tools.handlers import handle_human_override
        try:
            result = await handle_human_override({
                "agent_id": self.AGENT_ID,
                "action": task.get("type", "unknown"),
                "risk_level": output.risk_level,
                "risk_score": output.confidence_score,
                "context": {
                    "task": task,
                    "rationale": output.rationale,
                    "escalation_reason": output.escalation_reason,
                },
            })
            logger.warning("[OVERRIDE] %s queued request_id=%s — action BLOCKED",
                           self.AGENT_ID, result.get("request_id"))
            request_id = result.get("request_id")
            if require_record and not request_id:
                raise GovernanceUnavailableError("human override handler returned no request_id")
            return request_id
        except Exception as e:
            if require_record:
                if isinstance(e, GovernanceUnavailableError):
                    raise
                raise GovernanceUnavailableError(f"human approval unavailable for {self.AGENT_ID}: {e}") from e
            logger.error("[OVERRIDE_FAILURE] %s: %s", self.AGENT_ID, e)
            return None

    async def publish_event(self, event: AgentEvent) -> None:
        validate_confidence_attached({"confidence_score": event.confidence_score})
        logger.info("[EVENT] %s published %s (risk=%s)", self.AGENT_ID, event.event_type, event.risk_level)
        from .tools.handlers import handle_event_bus
        try:
            await handle_event_bus({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "producer_agent_id": self.AGENT_ID,
                "payload": event.payload if isinstance(event.payload, dict) else {"data": str(event.payload)},
                "confidence_score": event.confidence_score,
                "risk_level": event.risk_level,
                "requires_ack": event.requires_ack if hasattr(event, "requires_ack") else False,
                "correlation_id": event.correlation_id if hasattr(event, "correlation_id") else None,
            })
        except Exception as e:
            logger.error("[EVENT_PUBLISH_FAILURE] %s: %s", self.AGENT_ID, e)

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> Any:
        logger.info("[TOOL] %s calling %s", self.AGENT_ID, tool_name)
        from .tool_registry import execute_tool
        # Inject agent_id so handlers can use it without trusting the LLM's input
        enriched = {**tool_input, "agent_id": self.AGENT_ID}
        try:
            return await execute_tool(self.AGENT_ID, tool_name, enriched)
        except PermissionError as e:
            logger.warning("[TOOL_DENIED] %s → %s: %s", self.AGENT_ID, tool_name, e)
            # Write a real audit entry for the denied attempt
            try:
                from .tools.handlers import handle_audit_log
                await handle_audit_log({
                    "agent_id": self.AGENT_ID,
                    "action_type": "decision",
                    "input_summary": f"TOOL_DENIED: {tool_name}",
                    "output_summary": str(e)[:500],
                    "confidence_score": 0.0,
                    "risk_level": "high",
                    "session_id": self.session_id,
                })
            except Exception:
                pass
            raise
