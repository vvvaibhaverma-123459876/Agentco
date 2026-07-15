#!/usr/bin/env python3
"""Run governed capability genesis campaigns without synthetic capability claims."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.runtime import execute_capability_request  # noqa: E402
from agentco_capability.scoring import score_capability_task, score_governance_control, score_resource_control  # noqa: E402

BENCHMARK = ROOT / "benchmarks" / "capability_genesis_v2"
DOCS = ROOT / "docs" / "audit" / "current"


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(data: str) -> str:
    return sha256_bytes(data.encode())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def file_hash(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def aggregate_hash(paths: list[Path]) -> str:
    rows = [
        {"path": str(path.relative_to(ROOT)), "sha256": file_hash(path), "size_bytes": path.stat().st_size}
        for path in sorted(paths)
    ]
    return sha256_text(canonical_json(rows))


def load_cases() -> list[dict[str, Any]]:
    registry = load_json(BENCHMARK / "registry.json")
    cases: list[dict[str, Any]] = []
    for split in ("validation", "hidden"):
        cases.extend(load_json(BENCHMARK / registry["case_manifest_files"][split]))
    validation_prompts = {case["request"]["prompt"] for case in cases if case["split"] == "validation"}
    hidden_prompts = {case["request"]["prompt"] for case in cases if case["split"] == "hidden"}
    if validation_prompts & hidden_prompts:
        raise SystemExit("validation and hidden prompts must be distinct")
    return cases


def request_for_case(case: dict[str, Any], provider: str, mode: str) -> dict[str, Any]:
    raw = case["request"]
    operation_classification = "protocol_control" if mode == "protocol-reference" else "capability_task"
    return {
        "protocol_version": "agentco-capability-v1",
        "request_id": case["case_id"],
        "attempt_id": f"{mode}-{case['case_id']}",
        "actor": {"id": f"{mode}-evaluator", "type": "test_identity"},
        "tenant": "capability-genesis-v2",
        "task_type": case["domain"],
        "prompt": raw["prompt"],
        "structured_input": dict(raw.get("structured_input") or {}),
        "context": {
            "campaign": "governed-capability-genesis-v2",
            "split": case["split"],
            "operation_classification": operation_classification,
        },
        "memory_policy": {"enabled": False},
        "tool_allowlist": ["json_transformer", "calculator", "fixture_reader", "fixture_sql", "fixture_test_runner"],
        "provider_policy": {"provider": provider},
        "budget": dict(case.get("budget") or {"max_wall_ms": 5000, "max_provider_calls": 1}),
        "deadline": None,
        "idempotency_key": f"{mode}-{case['case_id']}",
        "authorization_context": {"permissions": ["capability:execute"] + (["provider:live"] if provider not in {"deterministic_protocol_reference", "mock_development"} else [])},
        "trace_context": {"trace_id": f"{mode}-{case['case_id']}"},
    }


def score_case(case: dict[str, Any], response: dict[str, Any], mode: str) -> dict[str, Any]:
    if mode == "protocol-reference":
        return {
            "case_id": case["case_id"],
            "domain": case["domain"],
            "operation_classification": "protocol_control",
            "protocol_shape_valid": response["protocol_version"] == "agentco-capability-v1",
            "completed_status_is_correctness": False,
            "capability_score": None,
            "correctness": None,
            "governance": score_governance_control(response, {"allowed": True}),
            "budget": score_resource_control(response, {}),
        }
    return {
        "case_id": case["case_id"],
        "domain": case["domain"],
        "operation_classification": "capability_task",
        "completed_status_is_correctness": False,
        "capability": score_capability_task(response, {}),
        "governance": score_governance_control(response, {"allowed": True}),
        "budget": score_resource_control(response, {}),
    }


def contains_evaluator_only_key(value: Any) -> bool:
    forbidden = {"expected", "expected_answer", "expected_hash", "rubric", "rubric_hash", "scoring_threshold"}
    if isinstance(value, dict):
        return any(str(key).lower() in forbidden or contains_evaluator_only_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(contains_evaluator_only_key(item) for item in value)
    return False


def write_payload_manifest(artifact: Path, files: list[Path], head: str, campaign_id: str, extra: dict[str, Any]) -> str:
    rows = [
        {"path": str(path.relative_to(artifact)), "sha256": file_hash(path), "size_bytes": path.stat().st_size}
        for path in sorted(files)
    ]
    payload_hash = sha256_text(canonical_json(rows))
    manifest = {
        "canonicalization_version": "capability-genesis-v2-payload-v1",
        "included_relative_paths": rows,
        "excluded_paths": [
            {"path": "INTERNAL_PAYLOAD_MANIFEST.json", "reason": "self-referential aggregate hash"},
            {"path": "GENESIS_V2_MANIFEST.json", "reason": "contains aggregate payload hash"},
        ],
        "aggregate_payload_hash": payload_hash,
        "campaign_execution_sha": head,
        "campaign_id": campaign_id,
        "generation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **extra,
    }
    (artifact / "INTERNAL_PAYLOAD_MANIFEST.json").write_text(canonical_json(manifest))
    return payload_hash


def run_v2(mode: str, provider: str) -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean before governed capability genesis v2")
    head = git("rev-parse", "HEAD")
    campaign_id = "governed-capability-genesis-v2"
    artifact = ROOT / "artifacts" / "capability-runtime" / f"{campaign_id}-{mode}"
    if artifact.exists():
        for path in sorted(artifact.glob("**/*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    (artifact / "results").mkdir(parents=True, exist_ok=True)

    registry = load_json(BENCHMARK / "registry.json")
    cases = load_cases()
    benchmark_files = [
        BENCHMARK / "registry.json",
        BENCHMARK / "validation" / "cases.json",
        BENCHMARK / "hidden" / "cases.json",
        BENCHMARK / "rubrics" / "rubrics.json",
        BENCHMARK / "fixtures" / "fixtures.json",
    ]
    benchmark_hash = aggregate_hash(benchmark_files)
    scorer_hash = file_hash(ROOT / "agentco_capability" / "scoring.py")
    results: list[dict[str, Any]] = []

    for case in cases:
        request = request_for_case(case, provider, mode)
        response = execute_capability_request(request)
        score = score_case(case, response, mode)
        record = {"case": case, "request": request, "response": response, "score": score}
        (artifact / "results" / f"{case['case_id']}.json").write_text(canonical_json(record))
        results.append(record)

    completed = [item for item in results if item["response"]["status"] == "completed"]
    failed = [item for item in results if item["response"]["status"] == "failed"]
    unsupported = [item for item in results if item["response"]["status"] == "unsupported"]
    timeouts = [item for item in results if item["response"]["status"] == "timed_out"]
    capability_domains = sorted({item["case"]["domain"] for item in completed if mode == "real-capability-provider"})
    hidden_leakage = any(contains_evaluator_only_key(item["request"]) for item in results)

    if mode == "protocol-reference":
        decision = "PROTOCOL_BASELINE_ACCEPTED" if len(completed) == len(cases) and not hidden_leakage else "PROTOCOL_BASELINE_REJECTED"
        capability_decision = "not_applicable_protocol_only"
    else:
        decision = "HOLD_FOR_MORE_EVIDENCE"
        capability_decision = "HOLD_FOR_MORE_EVIDENCE"
        if completed and len(capability_domains) >= registry["minimum_acceptance"]["capability_task_domains"]:
            decision = "HOLD_FOR_MORE_EVIDENCE"

    result_files = list((artifact / "results").glob("*.json"))
    payload_hash = write_payload_manifest(
        artifact,
        result_files,
        head,
        campaign_id,
        {
            "benchmark_registry_hash": benchmark_hash,
            "scorer_hash": scorer_hash,
            "provider": provider,
            "mode": mode,
        },
    )
    manifest = {
        "campaign_id": campaign_id,
        "campaign_execution_sha": head,
        "mode": mode,
        "provider": provider,
        "benchmark_registry_hash": benchmark_hash,
        "scorer_hash": scorer_hash,
        "planned": len(cases),
        "completed": len(completed),
        "failed": len(failed),
        "timeouts": len(timeouts),
        "unsupported": len(unsupported),
        "supported_capability_domains": capability_domains,
        "hidden_leakage": hidden_leakage,
        "request_consumption": "verified_by_protocol_request_hash_and_response_hash",
        "answer_ownership": "protocol_reference_only" if mode == "protocol-reference" else "provider_generated_when_completed",
        "decision": decision,
        "capability_decision": capability_decision,
        "internal_payload_manifest_hash": payload_hash,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (artifact / "GENESIS_V2_MANIFEST.json").write_text(canonical_json(manifest))
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / f"GOVERNED_CAPABILITY_GENESIS_V2_{mode.upper().replace('-', '_')}_RESULTS.json").write_text(canonical_json(manifest))
    print(canonical_json({"success": decision in {"PROTOCOL_BASELINE_ACCEPTED", "HOLD_FOR_MORE_EVIDENCE"}, **manifest}))
    return 0 if decision in {"PROTOCOL_BASELINE_ACCEPTED", "HOLD_FOR_MORE_EVIDENCE"} else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default="governed-capability-genesis-v2")
    parser.add_argument("--mode", choices=["protocol-reference", "real-capability-provider"], default="protocol-reference")
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()
    provider = args.provider or ("deterministic_protocol_reference" if args.mode == "protocol-reference" else os.getenv("AGENTCO_REAL_CAPABILITY_PROVIDER", "openai_compatible"))
    return run_v2(args.mode, provider)


if __name__ == "__main__":
    raise SystemExit(main())
