from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


PROTOCOL_VERSION = "agentco-capability-v1"
STATUSES = {
    "completed",
    "failed",
    "timed_out",
    "cancelled",
    "denied",
    "budget_exceeded",
    "unsupported",
    "partially_completed",
}
CAPABILITY_DOMAINS = {
    "reasoning",
    "planning",
    "evidence_evaluation",
    "claim_grounding",
    "structured_transformation",
    "safe_tool_selection",
    "data_analysis",
    "software_engineering",
    "cross_domain_synthesis",
}


@dataclass(frozen=True)
class CapabilityRequest:
    protocol_version: str
    request_id: str
    attempt_id: str
    actor: dict[str, Any]
    tenant: str
    task_type: str
    prompt: str
    structured_input: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    memory_policy: dict[str, Any] = field(default_factory=dict)
    tool_allowlist: list[str] = field(default_factory=list)
    provider_policy: dict[str, Any] = field(default_factory=dict)
    budget: dict[str, Any] = field(default_factory=dict)
    deadline: str | None = None
    idempotency_key: str | None = None
    authorization_context: dict[str, Any] = field(default_factory=dict)
    trace_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CapabilityRequest":
        if raw.get("protocol_version") != PROTOCOL_VERSION:
            raise ValueError("protocol_version must be agentco-capability-v1")
        required = ["request_id", "attempt_id", "actor", "tenant", "task_type", "prompt"]
        missing = [key for key in required if key not in raw]
        if missing:
            raise ValueError(f"missing required fields: {', '.join(missing)}")
        if raw["task_type"] not in CAPABILITY_DOMAINS:
            raise ValueError(f"unsupported task_type: {raw['task_type']}")
        if not isinstance(raw["prompt"], str) or not raw["prompt"].strip():
            raise ValueError("prompt must be a non-empty string")
        return cls(
            protocol_version=raw["protocol_version"],
            request_id=str(raw["request_id"]),
            attempt_id=str(raw["attempt_id"]),
            actor=dict(raw["actor"]),
            tenant=str(raw["tenant"]),
            task_type=str(raw["task_type"]),
            prompt=raw["prompt"],
            structured_input=dict(raw.get("structured_input") or {}),
            context=dict(raw.get("context") or {}),
            memory_policy=dict(raw.get("memory_policy") or {}),
            tool_allowlist=list(raw.get("tool_allowlist") or []),
            provider_policy=dict(raw.get("provider_policy") or {}),
            budget=dict(raw.get("budget") or {}),
            deadline=raw.get("deadline"),
            idempotency_key=raw.get("idempotency_key"),
            authorization_context=dict(raw.get("authorization_context") or {}),
            trace_context=dict(raw.get("trace_context") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "attempt_id": self.attempt_id,
            "actor": self.actor,
            "tenant": self.tenant,
            "task_type": self.task_type,
            "prompt": self.prompt,
            "structured_input": self.structured_input,
            "context": self.context,
            "memory_policy": self.memory_policy,
            "tool_allowlist": self.tool_allowlist,
            "provider_policy": self.provider_policy,
            "budget": self.budget,
            "deadline": self.deadline,
            "idempotency_key": self.idempotency_key,
            "authorization_context": self.authorization_context,
            "trace_context": self.trace_context,
        }


CapabilityStatus = Literal[
    "completed",
    "failed",
    "timed_out",
    "cancelled",
    "denied",
    "budget_exceeded",
    "unsupported",
    "partially_completed",
]
