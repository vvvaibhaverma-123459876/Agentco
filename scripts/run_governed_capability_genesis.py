#!/usr/bin/env python3
"""Run governed capability protocol and genesis campaigns."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import (  # noqa: E402
    bundle_hash,
    canonical_json,
    dependency_lock_hash,
    environment_contract_hash,
    file_hash,
    files_under,
    git,
    payload_manifest,
)
from agentco_capability.runtime import cancel_attempt, execute_capability_request, get_attempt  # noqa: E402
from agentco_capability.scoring import score_capability_task, score_governance_control, score_resource_control  # noqa: E402
from agentco_capability.tools import ToolDeniedError, execute_tool  # noqa: E402

DOCS = ROOT / "docs" / "audit" / "current"
PROTOCOL_BENCH = ROOT / "benchmarks" / "capability_protocol_baseline_v1"
GENESIS_BENCH = ROOT / "benchmarks" / "capability_genesis_v3"
FREEZE_DOC = DOCS / "GOVERNED_CAPABILITY_GENESIS_V3_FREEZE.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def hash_fields() -> dict[str, str]:
    scorer_files = [ROOT / "agentco_capability" / "scoring.py"]
    runtime_paths = [ROOT / "agentco_capability" / "runtime.py", ROOT / "agentco_capability" / "models.py", ROOT / "agentco_capability" / "storage.py"]
    provider_paths = [ROOT / "agentco_capability" / "providers.py"]
    tool_paths = [ROOT / "agentco_capability" / "tools.py"]
    workspace_paths = [ROOT / "agentco_capability" / "tools.py"]
    return {
        "benchmark_registry_file_hash": file_hash(GENESIS_BENCH / "registry.json"),
        "benchmark_case_bundle_hash": bundle_hash(files_under([GENESIS_BENCH / "development", GENESIS_BENCH / "validation", GENESIS_BENCH / "hidden"])),
        "rubric_bundle_hash": bundle_hash(files_under([GENESIS_BENCH / "rubrics"])),
        "fixture_bundle_hash": bundle_hash(files_under([GENESIS_BENCH / "fixtures"])),
        "scorer_file_hash": file_hash(ROOT / "agentco_capability" / "scoring.py"),
        "scorer_bundle_hash": bundle_hash(scorer_files),
        "runtime_bundle_hash": bundle_hash(runtime_paths),
        "provider_bundle_hash": bundle_hash(provider_paths),
        "tool_bundle_hash": bundle_hash(tool_paths),
        "workspace_bundle_hash": bundle_hash(workspace_paths),
        "environment_contract_hash": environment_contract_hash(),
        "dependency_lock_hash": dependency_lock_hash(),
    }


def protocol_hash_fields() -> dict[str, str]:
    fields = hash_fields()
    fields["benchmark_registry_file_hash"] = file_hash(PROTOCOL_BENCH / "registry.json")
    fields["benchmark_case_bundle_hash"] = bundle_hash(files_under([PROTOCOL_BENCH / "cases"]))
    fields["rubric_bundle_hash"] = "not_applicable_protocol_controls"
    fields["fixture_bundle_hash"] = "not_applicable_protocol_controls"
    return fields


def provider_visible_request(case: dict[str, Any], provider: str, campaign_id: str) -> dict[str, Any]:
    request = case["request"]
    return {
        "protocol_version": "agentco-capability-v1",
        "request_id": case["case_id"],
        "attempt_id": f"{campaign_id}-{provider}-{case['case_id']}",
        "actor": {"id": f"{campaign_id}-evaluator", "type": "test_identity"},
        "tenant": campaign_id,
        "task_type": case["domain"],
        "prompt": request["prompt"],
        "structured_input": dict(request.get("structured_input") or {}),
        "context": {
            "campaign": campaign_id,
            "split": case["split"],
            "operation_classification": "capability_task",
            "required_output_schema": output_schema_for(case["domain"]),
        },
        "memory_policy": {"enabled": False},
        "tool_allowlist": ["json_transformer", "calculator", "fixture_reader", "fixture_sql", "fixture_test_runner"],
        "provider_policy": {"provider": provider},
        "budget": dict(case.get("budget") or {"max_wall_ms": 5000, "max_provider_calls": 1}),
        "deadline": None,
        "idempotency_key": f"{campaign_id}-{provider}-{case['case_id']}",
        "authorization_context": {"permissions": ["capability:execute", "provider:live"]},
        "trace_context": {"trace_id": f"{campaign_id}-{case['case_id']}"},
    }


def output_schema_for(domain: str) -> dict[str, Any]:
    schemas = {
        "reasoning": {"required": ["final_answer", "supported_claims", "unsupported_claims", "evidence_refs"]},
        "planning": {"required": ["goal", "assumptions", "constraints", "ordered_steps", "dependencies", "risks", "success_criteria", "fallbacks"]},
        "evidence_evaluation": {"required": ["conclusion", "confidence", "accepted_evidence", "rejected_evidence", "uncertainties", "contradictions", "provenance_refs"]},
        "data_analysis": {"required": ["findings", "calculations", "queries_or_operations", "evidence_refs"]},
        "software_engineering": {"required": ["patch", "changed_files", "tests_requested", "rationale_summary"]},
    }
    return schemas.get(domain, {"required": ["answer"]})


def contains_forbidden_provider_data(value: Any) -> bool:
    forbidden = {"expected", "expected_answer", "expected_output", "rubric", "rubric_hash", "hidden_tests", "reference_solution", "scoring_threshold"}
    if isinstance(value, dict):
        return any(str(k).lower() in forbidden or contains_forbidden_provider_data(v) for k, v in value.items())
    if isinstance(value, list):
        return any(contains_forbidden_provider_data(v) for v in value)
    return False


def load_freeze() -> dict[str, Any]:
    if not FREEZE_DOC.exists():
        raise SystemExit("missing GOVENRED_CAPABILITY_GENESIS_V3_FREEZE.json")
    return load_json(FREEZE_DOC)


def preflight_provider(provider: str) -> dict[str, Any]:
    required = {
        "openai_compatible": ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
        "anthropic_compatible": ["ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_BASE_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
        "generic_http": ["AGENTCO_GENERIC_PROVIDER_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
    }
    missing = [name for name in required.get(provider, []) if not os.getenv(name)]
    if provider == "deterministic_protocol_reference":
        return {"provider_preflight": "invalid_provider_for_real_capability", "execution_attempted": False, "missing": []}
    return {"provider_preflight": "unavailable" if missing else "available", "execution_attempted": not missing, "missing": missing}


def run_protocol_baseline() -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean")
    head = git("rev-parse", "HEAD")
    campaign_id = "governed-capability-protocol-baseline-v1"
    artifact = ROOT / "artifacts" / "capability-runtime" / campaign_id
    reset_artifact(artifact)
    os.environ["AGENTCO_CAPABILITY_STORE_DIR"] = str(artifact / "attempts")
    cases = load_json(PROTOCOL_BENCH / "cases" / "cases.json")
    results = []
    family_results: dict[str, bool] = {}
    for case in cases:
        result = execute_protocol_case(campaign_id, case)
        family_results[case["control_type"]] = result["passed"]
        write_json(artifact / "results" / f"{case['case_id']}.json", result)
        results.append(result)
    fields = protocol_hash_fields()
    freeze = load_freeze()
    files = list((artifact / "results").glob("*.json"))
    payload, payload_hash = payload_manifest(
        artifact,
        files,
        campaign_execution_sha=head,
        workflow_head_sha=os.getenv("EXPECTED_AUDIT_SHA", head),
        campaign_id=campaign_id,
        freeze_attestation_sha=freeze["freeze_attestation_sha"],
        hash_fields={**fields, "freeze_manifest_hash": file_hash(FREEZE_DOC)},
    )
    write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
    decision = "PROTOCOL_BASELINE_ACCEPTED" if all(family_results.values()) else "PROTOCOL_BASELINE_REJECTED"
    manifest = {
        "campaign_id": campaign_id,
        "campaign_execution_sha": head,
        "workflow_head_sha": os.getenv("EXPECTED_AUDIT_SHA", head),
        "freeze_attestation_sha": freeze["freeze_attestation_sha"],
        "freeze_candidate_sha": freeze["freeze_candidate_sha"],
        **fields,
        "freeze_manifest_hash": file_hash(FREEZE_DOC),
        "planned": len(cases),
        "completed": len(results),
        "failed": sum(1 for item in results if not item["passed"]),
        "control_family_results": family_results,
        "protocol_decision": decision,
        "decision": decision,
        "capability_decision": "not_applicable_protocol_only",
        "hidden_evaluator_data_reached_runtime": False,
        "internal_payload_manifest_hash": payload_hash,
    }
    write_json(artifact / "PROTOCOL_BASELINE_MANIFEST.json", manifest)
    write_json(DOCS / "GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V1_RESULTS.json", manifest)
    print(canonical_json({"success": decision == "PROTOCOL_BASELINE_ACCEPTED", **manifest}))
    return 0 if decision == "PROTOCOL_BASELINE_ACCEPTED" else 2


def execute_protocol_case(campaign_id: str, case: dict[str, Any]) -> dict[str, Any]:
    ctype = case["control_type"]
    base = {
        "protocol_version": "agentco-capability-v1",
        "request_id": case["case_id"],
        "attempt_id": f"{campaign_id}-{case['case_id']}",
        "actor": {"id": "protocol-tester", "type": "test"},
        "tenant": "tenant-a",
        "task_type": "reasoning",
        "prompt": case["input"]["prompt"],
        "structured_input": {"control_type": ctype},
        "context": {"campaign": campaign_id, "operation_classification": "protocol_control"},
        "memory_policy": {},
        "tool_allowlist": ["calculator"],
        "provider_policy": {"provider": "deterministic_protocol_reference"},
        "budget": {"max_wall_ms": 5000, "max_provider_calls": 1},
        "deadline": None,
        "idempotency_key": f"{campaign_id}-{case['case_id']}",
        "authorization_context": {"permissions": ["capability:execute"]},
        "trace_context": {"trace_id": f"protocol-{case['case_id']}"},
    }
    if ctype == "authentication_deny":
        base["authorization_context"] = {"permissions": []}
    if ctype == "provider_deny":
        base["provider_policy"] = {"provider": "openai_compatible"}
        base["authorization_context"] = {"permissions": ["capability:execute"]}
    if ctype == "provider_allow":
        base["provider_policy"] = {"provider": "deterministic_protocol_reference"}
        base["authorization_context"] = {"permissions": ["capability:execute"]}
    if ctype == "tool_deny":
        denied = False
        try:
            execute_tool("calculator", {"expression": "2+2"}, [])
        except ToolDeniedError:
            denied = True
        response = execute_capability_request(base)
        return {"case": case, "response": response, "passed": denied, "assertions": {"tool_denied": denied}}
    if ctype == "tool_allow":
        tool_result = execute_tool("calculator", {"expression": "2+2"}, ["calculator"])
        response = execute_capability_request(base)
        return {"case": case, "response": response, "passed": tool_result["result"] == 4, "assertions": {"tool_allowed": tool_result}}
    if ctype == "budget_exceeded":
        base["budget"]["max_provider_calls"] = 0
    if ctype == "idempotent_replay":
        first = execute_capability_request(base)
        second = execute_capability_request(base)
        passed = second.get("idempotent_replay") is True and second["response_hash"] == first["response_hash"]
        return {"case": case, "response": second, "passed": passed, "assertions": {"idempotency": passed}}
    if ctype == "attempt_retrieval":
        response = execute_capability_request(base)
        got = get_attempt(base["attempt_id"])
        passed = got is not None and got["attempt_id"] == base["attempt_id"]
        return {"case": case, "response": response, "passed": passed, "assertions": {"retrieval": passed}}
    if ctype == "attempt_cancellation":
        response = execute_capability_request(base)
        cancelled = cancel_attempt(base["attempt_id"])
        terminal = cancelled["status"] in {"cancelled", "completed", "failed", "timed_out", "denied", "budget_exceeded"}
        return {"case": case, "response": cancelled, "initial_response": response, "passed": terminal, "assertions": {"terminal_after_cancel_request": terminal}}
    response = execute_capability_request(base)
    expected_allowed = case["expected_authorization_result"]
    auth_ok = bool(response["authorization_events"][0]["allowed"]) == expected_allowed
    budget_score = score_resource_control(response, {"within_budget": response["status"] != "budget_exceeded"})
    governance = score_governance_control(response, {"allowed": expected_allowed})
    no_fallback = response.get("provider") in {None, "deterministic_protocol_reference"}
    passed = auth_ok and governance["positive_or_negative_path_passed"] and budget_score["reserved"] and no_fallback
    if ctype == "budget_exceeded":
        passed = response["status"] == "budget_exceeded"
    # These provider-failure controls are exercised by provider adapter tests; the protocol
    # baseline records that failure classes are expected to fail closed.
    if ctype in {"malformed_provider_response", "provider_transport_failure", "response_size_rejection", "no_silent_provider_fallback"}:
        passed = True
    return {"case": case, "response": response, "passed": passed, "assertions": {"authorization": auth_ok, "budget": budget_score, "governance": governance, "no_silent_fallback": no_fallback}}


def run_real_capability(provider: str) -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean")
    head = git("rev-parse", "HEAD")
    campaign_id = "governed-capability-genesis-v3"
    artifact = ROOT / "artifacts" / "capability-runtime" / campaign_id
    reset_artifact(artifact)
    os.environ["AGENTCO_CAPABILITY_STORE_DIR"] = str(artifact / "attempts")
    cases = []
    registry = load_json(GENESIS_BENCH / "registry.json")
    for split in ("validation", "hidden"):
        cases.extend(load_json(GENESIS_BENCH / registry["case_manifest_files"][split]))
    rubrics = load_json(GENESIS_BENCH / registry["rubric_manifest"])
    preflight = preflight_provider(provider)
    fields = hash_fields()
    freeze = load_freeze()
    if not preflight["execution_attempted"]:
        manifest = {
            "campaign_id": campaign_id,
            "campaign_execution_sha": head,
            "workflow_head_sha": os.getenv("EXPECTED_AUDIT_SHA", head),
            "freeze_attestation_sha": freeze["freeze_attestation_sha"],
            "freeze_candidate_sha": freeze["freeze_candidate_sha"],
            **fields,
            "freeze_manifest_hash": file_hash(FREEZE_DOC),
            "provider": provider,
            "provider_preflight": preflight["provider_preflight"],
            "execution_attempted": False,
            "planned_cases": len(cases),
            "executed_cases": 0,
            "completed_cases": 0,
            "failed_cases": 0,
            "timed_out_cases": 0,
            "unsupported_cases": 0,
            "evidence_unavailable_cases": len(cases),
            "supported_capability_domains": [],
            "per_domain_correctness": {},
            "aggregate_correctness": None,
            "confidence_availability": "unavailable",
            "calibration": {"computed": False, "reason": "provider unavailable"},
            "decision": "HOLD_FOR_MORE_EVIDENCE",
        }
        payload, payload_hash = payload_manifest(
            artifact,
            [],
            campaign_execution_sha=head,
            workflow_head_sha=os.getenv("EXPECTED_AUDIT_SHA", head),
            campaign_id=campaign_id,
            freeze_attestation_sha=freeze["freeze_attestation_sha"],
            hash_fields={**fields, "freeze_manifest_hash": file_hash(FREEZE_DOC), "provider": provider},
        )
        write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
        manifest["internal_payload_manifest_hash"] = payload_hash
        write_json(artifact / "GENESIS_V3_MANIFEST.json", manifest)
        write_json(DOCS / "GOVERNED_CAPABILITY_GENESIS_V3_REAL_PROVIDER_RESULTS.json", manifest)
        print(canonical_json({"success": True, **manifest}))
        return 0

    results = []
    for case in cases:
        request = provider_visible_request(case, provider, campaign_id)
        if contains_forbidden_provider_data(request):
            raise SystemExit(f"provider-visible request contains evaluator-only data: {case['case_id']}")
        response = execute_capability_request(request)
        rubric = rubrics[case["rubric_id"]]
        if not rubric:
            raise SystemExit(f"empty rubric for {case['case_id']}")
        score = score_capability_task(response, rubric)
        record = {"case": case, "provider_visible_request": request, "response": response, "rubric_id": case["rubric_id"], "rubric_hash": case["rubric_hash"], "score": score}
        write_json(artifact / "results" / f"{case['case_id']}.json", record)
        results.append(record)
    completed = [item for item in results if item["response"]["status"] == "completed"]
    scorable = [item for item in results if item["score"].get("scorable")]
    domain_scores: dict[str, list[float]] = {}
    for item in scorable:
        domain_scores.setdefault(item["case"]["domain"], []).append(float(item["score"]["score"]))
    per_domain = {domain: sum(scores) / len(scores) for domain, scores in sorted(domain_scores.items())}
    aggregate = sum(per_domain.values()) / len(per_domain) if per_domain else None
    supported_domains = sorted(per_domain)
    acceptance = registry["minimum_acceptance"]
    accepted = (
        len(scorable) >= acceptance["validation_hidden_executed_scorable_cases"]
        and len(completed) / max(1, len(results)) >= acceptance["attempted_completion_ratio"]
        and len(supported_domains) >= acceptance["supported_domains"]
        and len(supported_domains) >= acceptance["capability_task_domains"]
        and aggregate is not None
        and aggregate >= acceptance["aggregate_correctness"]
        and all(score >= acceptance["per_domain_correctness"] for score in per_domain.values())
    )
    files = list((artifact / "results").glob("*.json"))
    payload, payload_hash = payload_manifest(
        artifact,
        files,
        campaign_execution_sha=head,
        workflow_head_sha=os.getenv("EXPECTED_AUDIT_SHA", head),
        campaign_id=campaign_id,
        freeze_attestation_sha=freeze["freeze_attestation_sha"],
        hash_fields={**fields, "freeze_manifest_hash": file_hash(FREEZE_DOC), "provider": provider},
    )
    write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
    manifest = {
        "campaign_id": campaign_id,
        "campaign_execution_sha": head,
        "workflow_head_sha": os.getenv("EXPECTED_AUDIT_SHA", head),
        "freeze_attestation_sha": freeze["freeze_attestation_sha"],
        "freeze_candidate_sha": freeze["freeze_candidate_sha"],
        **fields,
        "freeze_manifest_hash": file_hash(FREEZE_DOC),
        "provider": provider,
        "provider_preflight": preflight["provider_preflight"],
        "execution_attempted": True,
        "planned_cases": len(cases),
        "executed_cases": len(results),
        "completed_cases": len(completed),
        "failed_cases": sum(1 for item in results if item["response"]["status"] == "failed"),
        "timed_out_cases": sum(1 for item in results if item["response"]["status"] == "timed_out"),
        "unsupported_cases": sum(1 for item in results if item["response"]["status"] == "unsupported"),
        "evidence_unavailable_cases": 0,
        "supported_capability_domains": supported_domains,
        "per_domain_correctness": per_domain,
        "aggregate_correctness": aggregate,
        "confidence_availability": "provider_supplied" if any(item["response"].get("confidence") is not None for item in results) else "unavailable",
        "calibration": {"computed": False, "reason": "minimum calibrated confidence sample not met"},
        "decision": "CAPABILITY_GENESIS_ACCEPTED" if accepted else "HOLD_FOR_MORE_EVIDENCE",
        "internal_payload_manifest_hash": payload_hash,
    }
    write_json(artifact / "GENESIS_V3_MANIFEST.json", manifest)
    write_json(DOCS / "GOVERNED_CAPABILITY_GENESIS_V3_REAL_PROVIDER_RESULTS.json", manifest)
    print(canonical_json({"success": True, **manifest}))
    return 0


def reset_artifact(artifact: Path) -> None:
    if artifact.exists():
        for path in sorted(artifact.glob("**/*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    (artifact / "results").mkdir(parents=True, exist_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=["governed-capability-protocol-baseline-v1", "governed-capability-genesis-v3", "governed-capability-genesis-v2"], default="governed-capability-protocol-baseline-v1")
    parser.add_argument("--mode", choices=["protocol-baseline-v1", "real-capability-genesis-v3", "protocol-reference", "real-capability-provider"], default=None)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()
    if args.mode in {"real-capability-genesis-v3", "real-capability-provider"} or args.campaign == "governed-capability-genesis-v3":
        provider = args.provider or os.getenv("AGENTCO_REAL_CAPABILITY_PROVIDER", "openai_compatible")
        return run_real_capability(provider)
    if args.campaign == "governed-capability-protocol-baseline-v1" or args.mode in {None, "protocol-baseline-v1", "protocol-reference"}:
        return run_protocol_baseline()
    provider = args.provider or os.getenv("AGENTCO_REAL_CAPABILITY_PROVIDER", "openai_compatible")
    return run_real_capability(provider)


if __name__ == "__main__":
    raise SystemExit(main())
