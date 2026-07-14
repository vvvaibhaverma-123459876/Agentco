from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from .models import CapabilityRequest
from .tools import execute_tool, summarize_csv


class ProviderError(RuntimeError):
    pass


class CapabilityProvider:
    provider_type = "abstract"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        raise NotImplementedError


def stable_confidence(request: CapabilityRequest) -> float:
    digest = hashlib.sha256(json.dumps(request.to_dict(), sort_keys=True).encode()).hexdigest()
    return round(0.55 + (int(digest[:4], 16) % 35) / 100, 3)


class DeterministicLocalReferenceProvider(CapabilityProvider):
    provider_type = "deterministic_local_reference"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        started = time.time()
        task = request.task_type
        tool_calls: list[dict[str, Any]] = []
        answer: Any
        structured: dict[str, Any]
        evidence = [{"type": "request_prompt_hash", "sha256": hashlib.sha256(request.prompt.encode()).hexdigest()}]

        if task == "reasoning":
            answer = self._reason(request.prompt)
            structured = {"premises": self._sentences(request.prompt), "answer": answer}
        elif task == "planning":
            structured = self._plan(request)
            answer = structured["summary"]
        elif task == "evidence_evaluation":
            structured = self._evaluate_evidence(request.structured_input)
            answer = structured["conclusion"]
        elif task == "claim_grounding":
            structured = self._ground_claim(request.structured_input)
            answer = structured["grounding_status"]
        elif task == "structured_transformation":
            transformed = execute_tool(
                "json_transformer",
                {"mode": "sort_keys", "data": request.structured_input.get("data", request.structured_input)},
                request.tool_allowlist,
            )
            tool_calls.append({"tool": "json_transformer", "status": "completed"})
            structured = transformed
            answer = transformed["data"]
        elif task == "safe_tool_selection":
            structured = self._tool_decision(request)
            answer = structured["decision"]
        elif task == "data_analysis":
            csv_text = str(request.structured_input.get("csv", ""))
            structured = {"analysis": summarize_csv(csv_text)}
            answer = structured["analysis"]
        elif task == "software_engineering":
            structured = self._software_patch(request)
            answer = structured["patch"]
        elif task == "cross_domain_synthesis":
            structured = self._synthesis(request)
            answer = structured["synthesis"]
        else:
            raise ProviderError(f"unsupported task_type: {task}")

        latency_ms = round((time.time() - started) * 1000, 3)
        return {
            "answer": answer,
            "structured_output": structured,
            "confidence": stable_confidence(request),
            "evidence": evidence,
            "citations": [item.get("id") for item in request.structured_input.get("evidence", []) if isinstance(item, dict) and item.get("id")],
            "tool_calls": tool_calls,
            "provider": self.provider_type,
            "model": "agentco-deterministic-reference-v1",
            "latency": {"provider_ms": latency_ms},
        }

    @staticmethod
    def _sentences(text: str) -> list[str]:
        return [part.strip() for part in text.replace("?", ".").split(".") if part.strip()]

    def _reason(self, prompt: str) -> str:
        sentences = self._sentences(prompt)
        if any(word in prompt.lower() for word in ["not enough", "insufficient", "unknown"]):
            return "abstain: insufficient information"
        return f"deterministic conclusion from {len(sentences)} prompt statement(s)"

    def _plan(self, request: CapabilityRequest) -> dict[str, Any]:
        constraints = request.structured_input.get("constraints") or []
        return {
            "goal": request.prompt,
            "assumptions": ["inputs are synthetic and non-sensitive"],
            "constraints": constraints,
            "ordered_steps": [
                "validate request authority and budget",
                "collect available context and evidence",
                "execute allowed tools only when needed",
                "verify output against success criteria",
            ],
            "dependencies": request.structured_input.get("dependencies") or [],
            "risks": ["unsupported external boundary remains unavailable"],
            "success_criteria": request.structured_input.get("success_criteria") or ["bounded auditable answer"],
            "fallbacks": ["return compliant unsupported or failed status"],
            "summary": "validated four-step governed plan",
        }

    def _evaluate_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = list(payload.get("evidence") or [])
        accepted = []
        rejected = []
        support = 0.0
        contradict = 0.0
        for item in evidence:
            if not isinstance(item, dict):
                continue
            reliability = float(item.get("reliability", 0.5))
            stance = item.get("stance")
            if reliability >= 0.6:
                accepted.append(item.get("id"))
            else:
                rejected.append(item.get("id"))
            if stance == "support":
                support += reliability
            elif stance == "contradict":
                contradict += reliability
        if support > contradict + 0.2:
            conclusion = "supported"
        elif contradict > support + 0.2:
            conclusion = "contradicted"
        else:
            conclusion = "uncertain"
        return {
            "claim": payload.get("claim"),
            "conclusion": conclusion,
            "accepted_evidence": accepted,
            "rejected_evidence": rejected,
            "uncertainties": [] if conclusion != "uncertain" else ["support and contradiction are close"],
            "contradictions": [item.get("id") for item in evidence if isinstance(item, dict) and item.get("stance") == "contradict"],
        }

    def _ground_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        grounded = bool(payload.get("claim")) and bool(payload.get("evidence"))
        return {
            "grounding_status": "grounded" if grounded else "ungrounded",
            "claim": payload.get("claim"),
            "evidence_count": len(payload.get("evidence") or []),
        }

    def _tool_decision(self, request: CapabilityRequest) -> dict[str, Any]:
        prompt = request.prompt.lower()
        if "calculate" in prompt and "calculator" in request.tool_allowlist:
            return {"decision": "use_tool", "tool": "calculator", "reason": "calculation requested and tool is allowlisted"}
        return {"decision": "no_tool", "tool": None, "reason": "no allowlisted tool needed"}

    def _software_patch(self, request: CapabilityRequest) -> dict[str, Any]:
        target = request.structured_input.get("target_file", "solution.py")
        instruction = request.prompt.strip().replace("\n", " ")
        patch = f"--- a/{target}\n+++ b/{target}\n@@\n+# AgentCo deterministic patch plan: {instruction[:120]}\n"
        return {"changed_files": [target], "patch": patch, "tests_to_run": request.structured_input.get("tests", [])}

    def _synthesis(self, request: CapabilityRequest) -> dict[str, Any]:
        domains = request.structured_input.get("domains") or []
        return {
            "domains": domains,
            "synthesis": f"combined {len(domains)} domain(s) under governed deterministic policy",
        }


class MockDevelopmentProvider(DeterministicLocalReferenceProvider):
    provider_type = "mock_development"


class OpenAICompatibleProvider(CapabilityProvider):
    provider_type = "openai_compatible"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        if not os.getenv("OPENAI_API_KEY"):
            raise ProviderError("OPENAI_API_KEY is required for openai_compatible provider")
        raise ProviderError("live OpenAI-compatible execution is opt-in and not exercised by local genesis")


class AnthropicCompatibleProvider(CapabilityProvider):
    provider_type = "anthropic_compatible"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise ProviderError("ANTHROPIC_API_KEY is required for anthropic_compatible provider")
        raise ProviderError("live Anthropic-compatible execution is opt-in and not exercised by local genesis")


class GenericHTTPProvider(CapabilityProvider):
    provider_type = "generic_http"

    def execute(self, request: CapabilityRequest) -> dict[str, Any]:
        if not os.getenv("AGENTCO_GENERIC_PROVIDER_URL"):
            raise ProviderError("AGENTCO_GENERIC_PROVIDER_URL is required for generic_http provider")
        raise ProviderError("generic HTTP provider execution is opt-in and not exercised by local genesis")


def provider_from_policy(policy: dict[str, Any]) -> CapabilityProvider:
    provider = policy.get("provider", "deterministic_local_reference")
    if provider == "deterministic_local_reference":
        return DeterministicLocalReferenceProvider()
    if provider == "mock_development":
        return MockDevelopmentProvider()
    if provider == "openai_compatible":
        return OpenAICompatibleProvider()
    if provider == "anthropic_compatible":
        return AnthropicCompatibleProvider()
    if provider == "generic_http":
        return GenericHTTPProvider()
    raise ProviderError(f"unknown provider: {provider}")
