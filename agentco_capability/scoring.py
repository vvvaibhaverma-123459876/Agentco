from __future__ import annotations

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


def score_capability_task(response: dict[str, Any], rubric: dict[str, Any]) -> dict[str, Any]:
    if response.get("provider") == "deterministic_protocol_reference":
        return {
            "operation_classification": "capability_task",
            "scorable": False,
            "score": 0.0,
            "reason": "protocol reference provider cannot establish capability correctness",
        }
    expected = rubric.get("expected_answer")
    answer = response.get("answer")
    score = 1.0 if expected is not None and answer == expected else 0.0
    return {
        "operation_classification": "capability_task",
        "scorable": expected is not None,
        "score": score,
        "correctness": score,
        "reason": "exact expected-answer match" if score else "answer did not satisfy task-specific scorer",
    }


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
        "within_budget": usage.get("within_budget"),
        "reserved": usage.get("reserved"),
        "settled": usage.get("settled", response.get("status") in {"budget_exceeded", "denied"}),
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
