from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from .models import CapabilityRequest, PROTOCOL_VERSION
from .providers import ProviderError, provider_from_policy
from .storage import cancel_stored_attempt, read_attempt, write_attempt


def _hash(data: Any) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _authorization(request: CapabilityRequest) -> dict[str, Any]:
    permissions = set(request.authorization_context.get("permissions") or [])
    actor_id = request.actor.get("id")
    allowed = bool(actor_id) and "capability:execute" in permissions
    if request.provider_policy.get("provider") not in {None, "deterministic_local_reference", "mock_development"}:
        allowed = allowed and "provider:live" in permissions
    return {
        "actor_id": actor_id,
        "tenant": request.tenant,
        "allowed": allowed,
        "permission": "capability:execute",
        "reason": "authorized" if allowed else "missing capability:execute permission or actor id",
    }


def _budget_reservation(request: CapabilityRequest) -> dict[str, Any]:
    max_wall_ms = float(request.budget.get("max_wall_ms", 5000))
    max_tool_calls = int(request.budget.get("max_tool_calls", len(request.tool_allowlist) or 0))
    max_provider_calls = int(request.budget.get("max_provider_calls", 1))
    max_tokens = int(request.budget.get("max_tokens", 2048))
    return {
        "reserved": True,
        "max_wall_ms": max_wall_ms,
        "max_tool_calls": max_tool_calls,
        "max_provider_calls": max_provider_calls,
        "max_tokens": max_tokens,
        "provider_calls": 1,
        "tool_calls": 0,
        "within_budget": True,
    }


def _memory_events(request: CapabilityRequest) -> list[dict[str, Any]]:
    policy = request.memory_policy or {}
    if not policy.get("enabled"):
        return [{"event": "memory_skipped", "reason": "memory_policy_disabled"}]
    memories = [item for item in policy.get("memories", []) if item.get("verified") is True]
    return [
        {
            "event": "memory_retrieved",
            "memory_id": item.get("id"),
            "eligible": True,
            "relevance": item.get("relevance", 0.5),
            "affected_response": bool(item.get("content")),
        }
        for item in memories
    ] or [{"event": "memory_skipped", "reason": "no_verified_eligible_memory"}]


def _failure(status: str, message: str) -> dict[str, Any]:
    return {"type": status, "message": message, "recoverable": status not in {"denied", "budget_exceeded"}}


def execute_capability_request(raw: dict[str, Any]) -> dict[str, Any]:
    request = CapabilityRequest.from_dict(raw)
    if request.idempotency_key:
        existing = read_attempt(request.attempt_id)
        if existing and existing.get("idempotency_key") == request.idempotency_key:
            existing["idempotent_replay"] = True
            return existing

    started = time.time()
    authorization = _authorization(request)
    budget = _budget_reservation(request)
    base = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request.request_id,
        "attempt_id": request.attempt_id,
        "actor": request.actor,
        "tenant": request.tenant,
        "task_type": request.task_type,
        "idempotency_key": request.idempotency_key,
        "request": request.to_dict(),
        "authorization_events": [authorization],
        "budget_usage": budget,
        "memory_events": _memory_events(request),
        "trace_context": request.trace_context,
    }

    if not authorization["allowed"]:
        response = {
            **base,
            "status": "denied",
            "answer": None,
            "structured_output": {},
            "confidence": None,
            "evidence": [],
            "citations": [],
            "tool_calls": [],
            "provider": None,
            "model": None,
            "latency": {"wall_clock_ms": round((time.time() - started) * 1000, 3)},
            "resource_usage": {"measurement_method": "process_wall_clock_only"},
            "failure": _failure("denied", authorization["reason"]),
            "recovery": {"retryable": False, "terminal": True},
            "audit_references": [],
        }
        response.update(write_attempt(response))
        return response

    if budget["max_provider_calls"] < 1:
        response = {
            **base,
            "status": "budget_exceeded",
            "answer": None,
            "structured_output": {},
            "confidence": None,
            "evidence": [],
            "citations": [],
            "tool_calls": [],
            "provider": None,
            "model": None,
            "latency": {"wall_clock_ms": round((time.time() - started) * 1000, 3)},
            "resource_usage": {"measurement_method": "process_wall_clock_only"},
            "failure": _failure("budget_exceeded", "provider call budget is zero"),
            "recovery": {"retryable": False, "terminal": True},
            "audit_references": [],
        }
        response.update(write_attempt(response))
        return response

    try:
        provider = provider_from_policy(request.provider_policy)
        provider_result = provider.execute(request)
        wall_ms = round((time.time() - started) * 1000, 3)
        budget["settled"] = True
        budget["actual_wall_ms"] = wall_ms
        budget["within_budget"] = wall_ms <= budget["max_wall_ms"]
        status = "completed" if budget["within_budget"] else "budget_exceeded"
        response = {
            **base,
            "status": status,
            "answer": provider_result["answer"],
            "structured_output": provider_result["structured_output"],
            "confidence": provider_result["confidence"],
            "evidence": provider_result["evidence"],
            "citations": provider_result["citations"],
            "tool_calls": provider_result["tool_calls"],
            "provider": provider_result["provider"],
            "model": provider_result["model"],
            "latency": {"wall_clock_ms": wall_ms, **provider_result.get("latency", {})},
            "resource_usage": {"measurement_method": "process_wall_clock_only"},
            "failure": None if status == "completed" else _failure("budget_exceeded", "wall-clock budget exceeded"),
            "recovery": {"retryable": status != "completed", "terminal": True},
            "audit_references": [],
        }
    except ProviderError as exc:
        response = {
            **base,
            "status": "unsupported",
            "answer": None,
            "structured_output": {},
            "confidence": None,
            "evidence": [],
            "citations": [],
            "tool_calls": [],
            "provider": request.provider_policy.get("provider"),
            "model": None,
            "latency": {"wall_clock_ms": round((time.time() - started) * 1000, 3)},
            "resource_usage": {"measurement_method": "process_wall_clock_only"},
            "failure": _failure("unsupported", str(exc)),
            "recovery": {"retryable": False, "terminal": True},
            "audit_references": [],
        }
    except Exception as exc:
        response = {
            **base,
            "status": "failed",
            "answer": None,
            "structured_output": {},
            "confidence": None,
            "evidence": [],
            "citations": [],
            "tool_calls": [],
            "provider": request.provider_policy.get("provider", "deterministic_local_reference"),
            "model": None,
            "latency": {"wall_clock_ms": round((time.time() - started) * 1000, 3)},
            "resource_usage": {"measurement_method": "process_wall_clock_only"},
            "failure": _failure("failed", str(exc)),
            "recovery": {"retryable": True, "terminal": True},
            "audit_references": [],
        }
    response["response_hash"] = _hash({key: response[key] for key in ("status", "answer", "structured_output", "confidence")})
    response.update(write_attempt(response))
    return response


def get_attempt(attempt_id: str) -> dict[str, Any] | None:
    return read_attempt(attempt_id)


def cancel_attempt(attempt_id: str) -> dict[str, Any]:
    return cancel_stored_attempt(attempt_id)
