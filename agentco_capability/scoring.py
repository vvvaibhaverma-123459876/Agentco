from __future__ import annotations

import json
import math
from typing import Any


CAPABILITY_TASKS = {
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


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    return json.dumps(value, sort_keys=True, default=str).lower()


def _contains_all(value: Any, terms: list[str]) -> bool:
    text = _text(value)
    return all(term.lower() in text for term in terms)


def _base(domain: str, score: float, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_classification": "capability_task",
        "domain": domain,
        "scorable": True,
        "score": round(max(0.0, min(1.0, score)), 6),
        "correctness": round(max(0.0, min(1.0, score)), 6),
        "evidence": evidence,
    }


def score_calibration_primitive(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    confidence = response.get("structured_output", {}).get("confidence")
    outcome = response.get("structured_output", {}).get("outcome")
    brier = response.get("structured_output", {}).get("brier_score")
    expected_brier = None
    if isinstance(confidence, (int, float)) and isinstance(outcome, (int, float)):
        expected_brier = (float(confidence) - float(outcome)) ** 2
    parity = expected_brier is not None and isinstance(brier, (int, float)) and math.isclose(float(brier), expected_brier)
    return {
        "operation": "calibration_calculation",
        "operation_classification": "runtime_primitive",
        "numerical_result_available": isinstance(brier, (int, float)),
        "formula_parity": parity,
        "brier_result": brier,
        "correctness": None,
        "capability_score": None,
    }


def score_storage_write(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    output = response.get("structured_output", {})
    return {
        "operation": "durable_observation_recording",
        "operation_classification": "storage_operation",
        "write_acknowledged": response.get("status") == "completed",
        "request_hash_preserved": bool(output.get("request_hash")),
        "payload_integrity": output.get("payload_hash") == expected.get("payload_hash") if expected.get("payload_hash") else None,
        "recorded_output_hash": output.get("recorded_output_hash"),
        "correctness": None,
        "brier_score": None,
        "capability_score": None,
    }


def score_reasoning(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("reasoning", "protocol reference provider cannot reason")
    answer = response.get("structured_output") or response.get("answer")
    expected = rubric.get("expected_final_answer")
    required = rubric.get("required_terms", [])
    unsupported = rubric.get("forbidden_terms", [])
    score = 0.0
    if expected is not None and _text(expected) in _text(answer):
        score += 0.6
    if required and _contains_all(answer, required):
        score += 0.3
    if not any(term.lower() in _text(answer) for term in unsupported):
        score += 0.1
    return _base("reasoning", score, {"expected_final_answer": expected, "required_terms": required})


def score_planning(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("planning", "protocol reference provider cannot plan")
    output = response.get("structured_output") or {}
    steps = output.get("ordered_steps") or response.get("answer") or []
    text = _text(steps)
    required = rubric.get("required_steps", [])
    generic = rubric.get("generic_template_terms", ["analyze", "execute", "review"])
    coverage = sum(1 for step in required if step.lower() in text) / max(1, len(required))
    generic_only = all(term in text for term in generic) and coverage < 0.5
    return _base("planning", 0.0 if generic_only else coverage, {"required_steps": required, "generic_only": generic_only})


def score_evidence_evaluation(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("evidence_evaluation", "protocol reference provider cannot evaluate evidence")
    output = response.get("structured_output") or {}
    score = 0.0
    if _text(output.get("conclusion")) == _text(rubric.get("expected_conclusion")):
        score += 0.35
    if set(output.get("accepted_evidence") or []) >= set(rubric.get("accepted_evidence") or []):
        score += 0.25
    if set(output.get("rejected_evidence") or []) >= set(rubric.get("rejected_evidence") or []):
        score += 0.25
    if output.get("uncertainties") or output.get("contradictions"):
        score += 0.15
    return _base("evidence_evaluation", score, rubric)


def score_claim_grounding(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("claim_grounding", "protocol reference provider cannot ground claims")
    output = response.get("structured_output") or {}
    claims = output.get("claims") or []
    if not claims:
        return _base("claim_grounding", 0.0, {"reason": "no claims scored"})
    correct = sum(1 for claim in claims if claim.get("supported") == rubric.get("supported"))
    citations = sum(1 for claim in claims if claim.get("evidence_refs"))
    return _base("claim_grounding", (correct + citations) / (2 * len(claims)), rubric)


def score_structured_transformation(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("structured_transformation", "protocol reference provider cannot transform task content")
    expected = rubric.get("expected_output")
    actual = response.get("structured_output", {}).get("result", response.get("structured_output"))
    return _base("structured_transformation", 1.0 if actual == expected else 0.0, {"expected_output": expected})


def score_safe_tool_selection(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("safe_tool_selection", "protocol reference provider cannot select tools")
    calls = response.get("tool_calls") or []
    required = rubric.get("required_tool")
    invoked = any(call.get("tool") == required and call.get("authorized") is True for call in calls)
    avoided = not any(call.get("authorized") is False and call.get("executed") is True for call in calls)
    used = _contains_all(response.get("structured_output") or response.get("answer"), rubric.get("required_output_terms", []))
    return _base("safe_tool_selection", (0.4 if invoked else 0) + (0.3 if avoided else 0) + (0.3 if used else 0), rubric)


def score_data_analysis(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("data_analysis", "protocol reference provider cannot analyze data")
    calculations = response.get("structured_output", {}).get("calculations") or {}
    expected = rubric.get("expected_calculations") or {}
    if not expected:
        return _base("data_analysis", 0.0, {"reason": "missing expected calculations"})
    correct = 0
    for key, value in expected.items():
        actual = calculations.get(key)
        if isinstance(actual, (int, float)) and isinstance(value, (int, float)) and math.isclose(float(actual), float(value), rel_tol=1e-6):
            correct += 1
        elif actual == value:
            correct += 1
    return _base("data_analysis", correct / len(expected), rubric)


def score_software_engineering(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("software_engineering", "protocol reference provider cannot patch software")
    output = response.get("structured_output") or {}
    patch = str(output.get("patch") or "")
    changed = bool(output.get("changed_files"))
    comment_only = patch.strip().startswith("#") or "pass" == patch.strip()
    public_ok = output.get("public_tests_passed") is True
    hidden_ok = output.get("hidden_tests_passed") is True
    return _base("software_engineering", (0.25 if patch and not comment_only else 0) + (0.25 if changed else 0) + (0.25 if public_ok else 0) + (0.25 if hidden_ok else 0), rubric)


def score_cross_domain_synthesis(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability("cross_domain_synthesis", "protocol reference provider cannot synthesize domains")
    output = response.get("structured_output") or response.get("answer")
    domains = rubric.get("required_domains", [])
    constraints = rubric.get("required_constraints", [])
    return _base("cross_domain_synthesis", 0.6 * (sum(1 for d in domains if d.lower() in _text(output)) / max(1, len(domains))) + 0.4 * (sum(1 for c in constraints if c.lower() in _text(output)) / max(1, len(constraints))), rubric)


DOMAIN_SCORERS = {
    "reasoning": score_reasoning,
    "planning": score_planning,
    "evidence_evaluation": score_evidence_evaluation,
    "claim_grounding": score_claim_grounding,
    "structured_transformation": score_structured_transformation,
    "safe_tool_selection": score_safe_tool_selection,
    "data_analysis": score_data_analysis,
    "software_engineering": score_software_engineering,
    "cross_domain_synthesis": score_cross_domain_synthesis,
}


def _not_capability(domain: str, reason: str) -> dict[str, Any]:
    return {
        "operation_classification": "capability_task",
        "domain": domain,
        "scorable": False,
        "score": 0.0,
        "correctness": 0.0,
        "reason": reason,
    }


def score_capability_task(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if not rubric:
        raise ValueError("capability scoring requires evaluator-only rubric")
    if response.get("provider") == "deterministic_protocol_reference":
        return _not_capability(str(rubric.get("domain") or response.get("task_type") or "unknown"), "protocol reference provider cannot establish capability correctness")
    domain = rubric.get("domain") or response.get("task_type")
    scorer = DOMAIN_SCORERS.get(domain)
    if scorer is None:
        return _not_capability(str(domain), "no domain scorer")
    return scorer(response, rubric)


def score_governance_control(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    expected_allowed = expected.get("allowed")
    actual_allowed = bool((response.get("authorization_events") or [{}])[0].get("allowed"))
    return {
        "operation_classification": "governance_control",
        "positive_or_negative_path_passed": actual_allowed == expected_allowed,
        "audit_evidence": bool(response.get("authorization_events")),
    }


def score_resource_control(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("budget_usage") or {}
    return {
        "operation_classification": "resource_control",
        "within_budget": usage.get("within_budget") == expected.get("within_budget", usage.get("within_budget")),
        "reserved": usage.get("reserved") is True,
        "settled": usage.get("settled", response.get("status") in {"budget_exceeded", "denied"}) is True,
    }


def score_memory_operation(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    events = response.get("memory_events") or []
    return {
        "operation_classification": "storage_retrieval",
        "eligible_memory_used": any(event.get("eligible") for event in events),
        "retrieval_evidence": events,
    }


def score_recovery_operation(response: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    recovery = response.get("recovery") or {}
    return {
        "operation_classification": "recovery_control",
        "terminal_state_recorded": recovery.get("terminal") is True,
        "retryable": recovery.get("retryable"),
        "failure_visible": response.get("failure") is not None or response.get("status") == "completed",
    }
