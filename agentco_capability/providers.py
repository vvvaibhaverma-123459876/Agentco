from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from .models import CapabilityRequest


class ProviderError(RuntimeError):
    pass


class ProviderConfigurationError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ProviderPreflightUnavailable(ProviderConfigurationError):
    pass


@dataclass(frozen=True)
class ProviderMetadata:
    provider_id: str
    provider_class: str
    supported_operations: list[str]
    unsupported_operations: list[str]
    capability_level: str
    network_requirement: str
    secret_requirement: str
    intended_use: str
    prohibited_claims: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "provider_class": self.provider_class,
            "supported_operations": self.supported_operations,
            "unsupported_operations": self.unsupported_operations,
            "capability_level": self.capability_level,
            "network_requirement": self.network_requirement,
            "secret_requirement": self.secret_requirement,
            "intended_use": self.intended_use,
            "prohibited_claims": self.prohibited_claims,
        }


class CapabilityProvider:
    provider_type = "abstract"
    metadata = ProviderMetadata(
        provider_id="abstract",
        provider_class="development_mock",
        supported_operations=[],
        unsupported_operations=["capability_task"],
        capability_level="none",
        network_requirement="none",
        secret_requirement="none",
        intended_use="base interface",
        prohibited_claims=["capability evidence"],
    )

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        raise NotImplementedError


class DeterministicProtocolReferenceProvider(CapabilityProvider):
    provider_type = "deterministic_protocol_reference"
    metadata = ProviderMetadata(
        provider_id="deterministic_protocol_reference",
        provider_class="protocol_reference",
        supported_operations=[
            "protocol_validation",
            "lifecycle_validation",
            "authorization_validation",
            "budget_validation",
            "tool_boundary_validation",
            "storage_validation",
            "audit_validation",
            "provider_contract_validation",
        ],
        unsupported_operations=[
            "reasoning_capability",
            "planning_capability",
            "evidence_evaluation_capability",
            "claim_grounding_capability",
            "data_analysis_capability",
            "software_engineering_capability",
            "cross_domain_synthesis_capability",
        ],
        capability_level="protocol_only",
        network_requirement="none",
        secret_requirement="none",
        intended_use="CI-safe protocol and control validation",
        prohibited_claims=[
            "general reasoning model",
            "nine-domain AI capability provider",
            "model calibration evidence",
            "capability baseline",
        ],
    )

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        started = time.time()
        if request.context.get("operation_classification") == "capability_task":
            raise ProviderError("deterministic_protocol_reference does not perform capability tasks")
        return {
            "answer": None,
            "structured_output": {
                "protocol_validated": True,
                "request_id": request.request_id,
                "task_type": request.task_type,
                "provider_metadata": self.metadata.to_dict(),
            },
            "confidence": None,
            "confidence_classification": "unavailable",
            "evidence": [{"type": "protocol_reference", "request_id": request.request_id}],
            "citations": [],
            "tool_calls": [],
            "provider": self.provider_type,
            "model": "agentco-deterministic-protocol-reference-v1",
            "latency": {"provider_ms": round((time.time() - started) * 1000, 3)},
            "usage": {},
        }


class MockDevelopmentProvider(DeterministicProtocolReferenceProvider):
    provider_type = "mock_development"
    metadata = ProviderMetadata(
        provider_id="mock_development",
        provider_class="development_mock",
        supported_operations=["development_contract_validation"],
        unsupported_operations=["production_capability_evidence"],
        capability_level="mock_only",
        network_requirement="none",
        secret_requirement="none",
        intended_use="local development fixtures",
        prohibited_claims=["production evidence", "capability baseline"],
    )


def _redacted_headers(raw: dict[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in raw.items():
        lowered = key.lower()
        redacted[key] = "[REDACTED]" if "authorization" in lowered or "key" in lowered or "token" in lowered else value
    return redacted


def _require_https_or_local(url: str) -> None:
    if url.startswith("https://"):
        return
    if url.startswith("http://127.0.0.1") or url.startswith("http://localhost"):
        return
    raise ProviderConfigurationError("provider URL must use HTTPS outside explicit local development")


def _check_host_allowlist(url: str, allowlist: list[str]) -> None:
    allowlist = [item.strip() for item in allowlist if item and item.strip()]
    if not allowlist:
        raise ProviderConfigurationError("provider host allowlist is required")
    host = urllib.parse.urlparse(url).hostname or ""
    if host not in allowlist:
        raise ProviderConfigurationError(f"provider host {host!r} is not allowlisted")


def _classify_http_error(code: int) -> tuple[str, bool]:
    if code in {408, 409, 425, 429} or 500 <= code <= 599:
        return f"retryable_http_{code}", True
    return f"non_retryable_http_{code}", False


def _post_json_once(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float, max_bytes: int) -> dict[str, Any]:
    body = json.dumps(payload, sort_keys=True).encode()
    request = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ProviderResponseError("provider response exceeded size limit")
            data = json.loads(raw.decode())
            data["_agentco_http_status"] = response.status
            data["_agentco_latency_ms"] = round((time.time() - started) * 1000, 3)
            return data
    except urllib.error.HTTPError as exc:
        classification, _retryable = _classify_http_error(exc.code)
        raise ProviderResponseError(classification) from exc
    except urllib.error.URLError as exc:
        raise ProviderResponseError(f"provider transport error: {exc.reason}") from exc
    except (TimeoutError, socket.timeout) as exc:
        raise ProviderResponseError("provider request timed out") from exc
    except json.JSONDecodeError as exc:
        raise ProviderResponseError("provider returned malformed JSON") from exc


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: float,
    max_bytes: int,
    max_retries: int,
    backoff_seconds: float,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    started_total = time.time()
    for attempt in range(max_retries + 1):
        started = time.time()
        try:
            data = _post_json_once(url, payload, headers, timeout, max_bytes)
            data["_agentco_retry_count"] = attempt
            data["_agentco_attempts"] = attempts + [{"attempt": attempt + 1, "status": "success", "latency_ms": round((time.time() - started) * 1000, 3)}]
            data["_agentco_total_latency_ms"] = round((time.time() - started_total) * 1000, 3)
            return data
        except ProviderResponseError as exc:
            message = str(exc)
            retryable = message.startswith("retryable_http_") or "transport error" in message or "timed out" in message
            attempts.append({"attempt": attempt + 1, "status": "failed", "error_classification": message, "retryable": retryable})
            if not retryable or attempt >= max_retries:
                raise
            time.sleep(min(backoff_seconds * (2**attempt), 2.0))
    raise ProviderResponseError("provider retry loop exhausted")


def _structured_prompt(request: CapabilityRequest) -> str:
    return json.dumps(
        {
            "task_type": request.task_type,
            "prompt": request.prompt,
            "structured_input": request.structured_input,
            "required_output_schema": request.context.get("required_output_schema", {}),
            "instructions": "Return a JSON object matching required_output_schema. Do not include hidden reasoning.",
        },
        sort_keys=True,
    )


def _validate_structured_output(answer: Any) -> None:
    if answer is None:
        raise ProviderResponseError("provider response missing answer")


class OpenAICompatibleProvider(CapabilityProvider):
    provider_type = "openai_compatible"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        model = os.getenv("OPENAI_MODEL")
        if not api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required for openai_compatible provider")
        if not model:
            raise ProviderConfigurationError("OPENAI_MODEL is required for openai_compatible provider")
        _require_https_or_local(base_url)
        _check_host_allowlist(base_url, os.getenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "").split(","))
        url = base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return concise JSON-compatible task output. Do not reveal secrets."},
                {"role": "user", "content": _structured_prompt(request)},
            ],
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0")),
            "max_tokens": int(request.budget.get("max_tokens", 512)),
        }
        headers = {"Authorization": f"Bearer {api_key}"}
        if os.getenv("OPENAI_ORG_ID"):
            headers["OpenAI-Organization"] = os.environ["OPENAI_ORG_ID"]
        if os.getenv("OPENAI_PROJECT_ID"):
            headers["OpenAI-Project"] = os.environ["OPENAI_PROJECT_ID"]
        data = _post_json(
            url,
            payload,
            headers,
            float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
            int(os.getenv("AGENTCO_PROVIDER_RESPONSE_MAX_BYTES", "1000000")),
            int(os.getenv("OPENAI_MAX_RETRIES", "2")),
            float(os.getenv("OPENAI_RETRY_BACKOFF_SECONDS", "0.1")),
        )
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        _validate_structured_output(message.get("content"))
        return {
            "answer": message.get("content"),
            "structured_output": {"raw_text": message.get("content"), "finish_reason": choice.get("finish_reason")},
            "confidence": None,
            "confidence_classification": "unavailable",
            "evidence": [{"type": "provider_response", "provider_response_id": data.get("id")}],
            "citations": [],
            "tool_calls": [],
            "provider": self.provider_type,
            "model": data.get("model", model),
            "latency": {"provider_ms": data.get("_agentco_total_latency_ms", data.get("_agentco_latency_ms")), "retry_count": data.get("_agentco_retry_count", 0), "attempts": data.get("_agentco_attempts", [])},
            "usage": data.get("usage") or {},
            "request_metadata": {"url": url, "headers": _redacted_headers(headers)},
        }


class AnthropicCompatibleProvider(CapabilityProvider):
    provider_type = "anthropic_compatible"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        model = os.getenv("ANTHROPIC_MODEL")
        if not api_key:
            raise ProviderConfigurationError("ANTHROPIC_API_KEY is required for anthropic_compatible provider")
        if not model:
            raise ProviderConfigurationError("ANTHROPIC_MODEL is required for anthropic_compatible provider")
        _require_https_or_local(base_url)
        _check_host_allowlist(base_url, os.getenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "").split(","))
        url = base_url.rstrip("/") + "/v1/messages"
        headers = {"x-api-key": api_key, "anthropic-version": os.getenv("ANTHROPIC_VERSION", "2023-06-01")}
        payload = {
            "model": model,
            "max_tokens": int(request.budget.get("max_tokens", 512)),
            "messages": [{"role": "user", "content": _structured_prompt(request)}],
        }
        data = _post_json(
            url,
            payload,
            headers,
            float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "30")),
            int(os.getenv("AGENTCO_PROVIDER_RESPONSE_MAX_BYTES", "1000000")),
            int(os.getenv("ANTHROPIC_MAX_RETRIES", "2")),
            float(os.getenv("ANTHROPIC_RETRY_BACKOFF_SECONDS", "0.1")),
        )
        text = "\n".join(part.get("text", "") for part in data.get("content", []) if isinstance(part, dict))
        _validate_structured_output(text)
        return {
            "answer": text,
            "structured_output": {"raw_text": text, "stop_reason": data.get("stop_reason")},
            "confidence": None,
            "confidence_classification": "unavailable",
            "evidence": [{"type": "provider_response", "provider_response_id": data.get("id")}],
            "citations": [],
            "tool_calls": [],
            "provider": self.provider_type,
            "model": data.get("model", model),
            "latency": {"provider_ms": data.get("_agentco_total_latency_ms", data.get("_agentco_latency_ms")), "retry_count": data.get("_agentco_retry_count", 0), "attempts": data.get("_agentco_attempts", [])},
            "usage": data.get("usage") or {},
            "request_metadata": {"url": url, "headers": _redacted_headers(headers)},
        }


class GenericHTTPProvider(CapabilityProvider):
    provider_type = "generic_http"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        url = os.getenv("AGENTCO_GENERIC_PROVIDER_URL")
        token = os.getenv("AGENTCO_GENERIC_PROVIDER_TOKEN")
        if not url:
            raise ProviderConfigurationError("AGENTCO_GENERIC_PROVIDER_URL is required for generic_http provider")
        _require_https_or_local(url)
        _check_host_allowlist(url, os.getenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "").split(","))
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        template = json.loads(os.getenv("AGENTCO_GENERIC_PROVIDER_TEMPLATE", "{}") or "{}")
        payload = {**template, "request": json.loads(_structured_prompt(request))}
        data = _post_json(
            url,
            payload,
            headers,
            float(os.getenv("AGENTCO_GENERIC_TIMEOUT_SECONDS", "30")),
            int(os.getenv("AGENTCO_PROVIDER_RESPONSE_MAX_BYTES", "1000000")),
            int(os.getenv("AGENTCO_GENERIC_MAX_RETRIES", "2")),
            float(os.getenv("AGENTCO_GENERIC_RETRY_BACKOFF_SECONDS", "0.1")),
        )
        answer_path = os.getenv("AGENTCO_GENERIC_ANSWER_FIELD", "answer")
        answer = data
        for part in answer_path.split("."):
            answer = answer.get(part) if isinstance(answer, dict) else None
        if answer is None:
            raise ProviderResponseError("generic provider response missing configured answer field")
        _validate_structured_output(answer)
        return {
            "answer": answer,
            "structured_output": {"raw_response": data},
            "confidence": None,
            "confidence_classification": "unavailable",
            "evidence": [{"type": "provider_response", "provider_response_id": data.get("id")}],
            "citations": [],
            "tool_calls": [],
            "provider": self.provider_type,
            "model": data.get("model"),
            "latency": {"provider_ms": data.get("_agentco_total_latency_ms", data.get("_agentco_latency_ms")), "retry_count": data.get("_agentco_retry_count", 0), "attempts": data.get("_agentco_attempts", [])},
            "usage": data.get("usage") or {},
            "request_metadata": {"url": url, "headers": _redacted_headers(headers)},
        }


def provider_from_policy(policy: dict[str, Any]) -> CapabilityProvider:
    provider = policy.get("provider", "deterministic_protocol_reference")
    if provider in {"deterministic_protocol_reference", "deterministic_local_reference"}:
        return DeterministicProtocolReferenceProvider()
    if provider == "mock_development":
        return MockDevelopmentProvider()
    if provider == "openai_compatible":
        return OpenAICompatibleProvider()
    if provider == "anthropic_compatible":
        return AnthropicCompatibleProvider()
    if provider == "generic_http":
        return GenericHTTPProvider()
    raise ProviderError(f"unknown provider: {provider}")
