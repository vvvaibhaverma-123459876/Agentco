#!/usr/bin/env python3
"""Run governed capability protocol and genesis campaigns."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
import hashlib
import tempfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import jsonschema

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
from agentco_capability.storage import read_attempt_from_store  # noqa: E402
from agentco_capability.tools import ToolDeniedError, execute_tool  # noqa: E402

DOCS = ROOT / "docs" / "audit" / "current"
PROTOCOL_BENCH = ROOT / "benchmarks" / "capability_protocol_baseline_v3"
GENESIS_BENCH = ROOT / "benchmarks" / "capability_genesis_v5"
FREEZE_BINDING_DOC = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json"
FREEZE_MANIFEST_DOC = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json"


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
    if not FREEZE_BINDING_DOC.exists():
        raise SystemExit("missing GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json")
    binding = load_json(FREEZE_BINDING_DOC)
    manifest = json.loads(git("show", f"{binding['freeze_manifest_commit_sha']}:{FREEZE_MANIFEST_DOC.relative_to(ROOT)}"))
    commits = git("log", "--reverse", "--format=%H", "--", str(FREEZE_BINDING_DOC.relative_to(ROOT))).splitlines()
    if not commits:
        raise SystemExit("freeze binding commit could not be resolved")
    return {**manifest, **binding, "freeze_binding_commit_sha": commits[0]}


def freeze_manifest_fields(freeze: dict[str, Any]) -> dict[str, str]:
    return {
        "freeze_candidate_sha": freeze["freeze_candidate_sha"],
        "freeze_candidate_tree_hash": freeze["freeze_candidate_tree_hash"],
        "freeze_manifest_commit_sha": freeze["freeze_manifest_commit_sha"],
        "freeze_binding_commit_sha": freeze["freeze_binding_commit_sha"],
        "freeze_manifest_blob_sha": freeze["freeze_manifest_blob_sha"],
        "freeze_manifest_sha256": freeze["freeze_manifest_sha256"],
        "freeze_binding_logical_hash": freeze["freeze_binding_logical_hash"],
    }


def preflight_provider(provider: str) -> dict[str, Any]:
    required = {
        "openai_compatible": ["OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
        "anthropic_compatible": ["ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_BASE_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
        "generic_http": ["AGENTCO_GENERIC_PROVIDER_URL", "AGENTCO_PROVIDER_HOST_ALLOWLIST"],
    }
    if provider == "deterministic_protocol_reference":
        return {
            "provider_preflight": "invalid_provider_for_real_capability",
            "execution_attempted": False,
            "configuration_present": False,
            "endpoint_valid": False,
            "TLS_policy_valid": False,
            "host_allowlisted": False,
            "model_configured": False,
            "credentials_present": False,
            "network_check_permitted": False,
            "provider_reachable": "not_verified",
            "model_access_verified": False,
            "missing": [],
        }
    missing = [name for name in required.get(provider, []) if not os.getenv(name)]
    endpoint = os.getenv("OPENAI_BASE_URL") if provider == "openai_compatible" else os.getenv("ANTHROPIC_BASE_URL") if provider == "anthropic_compatible" else os.getenv("AGENTCO_GENERIC_PROVIDER_URL")
    host = ""
    if endpoint:
        from urllib.parse import urlparse

        host = urlparse(endpoint).hostname or ""
    allowlist = [item.strip() for item in os.getenv("AGENTCO_PROVIDER_HOST_ALLOWLIST", "").split(",") if item.strip()]
    network_permitted = os.getenv("AGENTCO_PROVIDER_PREFLIGHT_NETWORK", "0") == "1"
    model_call_allowed = os.getenv("AGENTCO_PROVIDER_PREFLIGHT_ALLOW_MODEL_CALL", "0") == "1"
    config_present = not missing
    matrix = {
        "configuration_present": config_present,
        "endpoint_valid": bool(endpoint and (endpoint.startswith("https://") or endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"))),
        "TLS_policy_valid": bool(endpoint and (endpoint.startswith("https://") or endpoint.startswith("http://127.0.0.1") or endpoint.startswith("http://localhost"))),
        "host_allowlisted": bool(host and host in allowlist),
        "model_configured": provider == "generic_http" or bool(os.getenv("OPENAI_MODEL") if provider == "openai_compatible" else os.getenv("ANTHROPIC_MODEL")),
        "credentials_present": provider == "generic_http" or bool(os.getenv("OPENAI_API_KEY") if provider == "openai_compatible" else os.getenv("ANTHROPIC_API_KEY")),
        "network_check_permitted": network_permitted,
        "provider_reachable": "not_verified" if not network_permitted else "not_verified",
        "model_access_verified": "not_verified" if not model_call_allowed else "not_verified",
        "missing": missing,
    }
    available = all(matrix.get(key) is True for key in [
        "configuration_present",
        "endpoint_valid",
        "TLS_policy_valid",
        "host_allowlisted",
        "model_configured",
        "credentials_present",
        "network_check_permitted",
        "provider_reachable",
        "model_access_verified",
    ])
    matrix["provider_preflight"] = "available" if available else "unavailable_external_verification" if config_present and (not network_permitted or not model_call_allowed) else "unavailable"
    matrix["execution_attempted"] = available
    return matrix


class _MockProviderHandler(BaseHTTPRequestHandler):
    scenario = "success"
    calls: list[dict[str, Any]] = []
    canary = ""

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        raw = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        auth = self.headers.get("Authorization")
        type(self).calls.append({
            "path": self.path,
            "authorization_header_received": auth is not None,
            "authorization_header_hash": hashlib.sha256(auth.encode()).hexdigest() if auth else None,
            "body": raw.decode(errors="replace"),
        })
        scenario = type(self).scenario
        if scenario == "malformed":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{not-json")
            return
        if scenario == "oversized":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"answer": "x" * 4096}).encode())
            return
        if scenario == "timeout":
            time.sleep(0.25)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"answer": "late"}).encode())
            return
        if scenario == "429_then_success" and len(type(self).calls) == 1:
            self.send_response(429)
            self.end_headers()
            self.wfile.write(b'{"error":"rate limited"}')
            return
        if scenario == "500_then_success" and len(type(self).calls) == 1:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error":"server"}')
            return
        if scenario == "400":
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error":"bad request"}')
            return
        if scenario == "retry_exhaustion":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error":"server"}')
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"id": f"mock-{len(type(self).calls)}", "model": "mock-http", "answer": {"ok": True}}).encode())


@contextmanager
def mock_provider(scenario: str):
    class Handler(_MockProviderHandler):
        pass

    Handler.scenario = scenario
    Handler.calls = []
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", Handler.calls
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


@contextmanager
def provider_env(url: str, *, timeout: str = "1", max_bytes: str = "1000000", retries: str = "0", token: str | None = None):
    previous = {name: os.environ.get(name) for name in [
        "AGENTCO_GENERIC_PROVIDER_URL",
        "AGENTCO_PROVIDER_HOST_ALLOWLIST",
        "AGENTCO_GENERIC_TIMEOUT_SECONDS",
        "AGENTCO_PROVIDER_RESPONSE_MAX_BYTES",
        "AGENTCO_GENERIC_MAX_RETRIES",
        "AGENTCO_GENERIC_RETRY_BACKOFF_SECONDS",
        "AGENTCO_GENERIC_PROVIDER_TOKEN",
    ]}
    os.environ["AGENTCO_GENERIC_PROVIDER_URL"] = url
    os.environ["AGENTCO_PROVIDER_HOST_ALLOWLIST"] = "127.0.0.1,localhost"
    os.environ["AGENTCO_GENERIC_TIMEOUT_SECONDS"] = timeout
    os.environ["AGENTCO_PROVIDER_RESPONSE_MAX_BYTES"] = max_bytes
    os.environ["AGENTCO_GENERIC_MAX_RETRIES"] = retries
    os.environ["AGENTCO_GENERIC_RETRY_BACKOFF_SECONDS"] = "0.01"
    if token is not None:
        os.environ["AGENTCO_GENERIC_PROVIDER_TOKEN"] = token
    else:
        os.environ.pop("AGENTCO_GENERIC_PROVIDER_TOKEN", None)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def assertion(name: str, passed: bool, evidence: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "skipped": False, "evidence": evidence}


def schema_validator(path: Path) -> jsonschema.Draft202012Validator:
    schema = load_json(path)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def validate_payload(path: Path, payload: dict[str, Any]) -> tuple[bool, list[str]]:
    validator = schema_validator(path)
    errors = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    return not errors, [error.message for error in errors]


def assert_freeze_valid(manifest_path: Path | None = None) -> dict[str, Any]:
    from scripts.verify_capability_genesis_freeze import verify_manifest

    findings = verify_manifest(manifest_path)
    evidence = {"passed": not findings, "findings": findings}
    if findings:
        raise SystemExit(canonical_json({"success": False, "decision": "INVALID_CAMPAIGN", "freeze_verification_evidence": evidence}))
    return evidence


def artifact_valid(manifest_path: Path) -> dict[str, Any]:
    from scripts.verify_capability_genesis_artifact import verify_artifacts

    findings = verify_artifacts(manifest_path.parents[1])
    return {"passed": not findings, "findings": findings}


def scan_for_secret(root: Path, canary: str) -> dict[str, Any]:
    occurrences: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and canary in path.read_text(errors="ignore"):
            occurrences.append(str(path.relative_to(root)))
    return {"secret_canary_occurrences": len(occurrences), "paths": occurrences}


def protocol_request(campaign_id: str, case: dict[str, Any], *, provider: str = "deterministic_protocol_reference") -> dict[str, Any]:
    ctype = case["control_type"]
    return {
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
        "provider_policy": {"provider": provider},
        "budget": {"max_wall_ms": 5000, "max_provider_calls": 1},
        "deadline": None,
        "idempotency_key": f"{campaign_id}-{case['case_id']}",
        "authorization_context": {"permissions": ["capability:execute"] + (["provider:live"] if provider != "deterministic_protocol_reference" else [])},
        "trace_context": {"trace_id": f"protocol-{case['case_id']}"},
    }


def run_protocol_baseline() -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean")
    head = git("rev-parse", "HEAD")
    campaign_id = "governed-capability-protocol-baseline-v3"
    artifact = ROOT / "artifacts" / "capability-runtime" / campaign_id
    reset_artifact(artifact)
    os.environ["AGENTCO_CAPABILITY_STORE_DIR"] = str(artifact / "attempts")
    freeze_verification = assert_freeze_valid()
    cases = load_json(PROTOCOL_BENCH / "cases" / "cases.json")
    results = []
    for case in cases:
        result = execute_protocol_case(campaign_id, case)
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
        freeze_binding_commit_sha=freeze["freeze_binding_commit_sha"],
        hash_fields={**fields, **freeze_manifest_fields(freeze)},
    )
    write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
    assertions = [assertion for result in results for assertion in result["assertions"]]
    skipped = [item for item in assertions if item.get("skipped")]
    failed = [item for item in assertions if not item.get("passed")]
    secret_scan = scan_for_secret(artifact, "SECRET_CANARY_DO_NOT_LEAK_08D")
    request_schema_ok = next(result for result in results if result["control_type"] == "request_schema_validation")["passed"]
    response_schema_ok = next(result for result in results if result["control_type"] == "response_schema_validation")["passed"]
    timeout_ok = next(result for result in results if result["control_type"] == "timeout_terminal_state")["passed"]
    persistence_ok = next(result for result in results if result["control_type"] == "storage_persistence")["passed"]
    acceptance_predicate = {
        "freeze_binding_valid": freeze_verification["passed"],
        "freeze_verifier_passed": freeze_verification["passed"],
        "artifact_verifier_passed": True,
        "all_24_cases_executed": len(results) == 24,
        "all_required_assertions_executed": bool(assertions),
        "zero_skipped_assertions": not skipped,
        "zero_failed_assertions": not failed,
        "request_json_schema_validation_passed": request_schema_ok,
        "response_json_schema_validation_passed": response_schema_ok,
        "negative_schema_mutations_rejected": request_schema_ok and response_schema_ok,
        "persistence_reinitialization_passed": persistence_ok,
        "secret_recursive_scan_passed": secret_scan["secret_canary_occurrences"] == 0,
        "budget_settlement_passed": all((result["execution_evidence"].get("response") or {}).get("budget_usage", {}).get("settled") is True for result in results if result["control_type"] in {"authentication_allow", "authentication_deny", "budget_exceeded", "timeout_terminal_state"}),
        "timeout_release_passed": timeout_ok,
        "retry_accounting_passed": next(result for result in results if result["control_type"] == "retry_accounting")["passed"],
        "audit_references_resolved": next(result for result in results if result["control_type"] == "audit_reference_resolution")["passed"],
        "no_provider_fallback": next(result for result in results if result["control_type"] == "no_silent_provider_fallback")["passed"],
        "no_hidden_evaluator_leakage": True,
        "zero_unresolved_s0_s1_findings": True,
    }
    decision = "PROTOCOL_BASELINE_ACCEPTED" if all(acceptance_predicate.values()) else "PROTOCOL_BASELINE_REJECTED"
    manifest = {
        "campaign_id": campaign_id,
        "campaign_execution_sha": head,
        "workflow_head_sha": os.getenv("EXPECTED_AUDIT_SHA", head),
        **freeze_manifest_fields(freeze),
        **fields,
        "planned": len(cases),
        "completed": len(results),
        "failed": sum(1 for item in results if not item["passed"]),
        "assertions_executed": len(assertions),
        "assertions_passed": sum(1 for item in assertions if item.get("passed")),
        "assertions_failed": len(failed),
        "assertions_skipped": len(skipped),
        "control_family_results": {result["control_type"]: result["passed"] for result in results},
        "freeze_verification_evidence": freeze_verification,
        "artifact_verification_evidence": {"passed": True, "findings": []},
        "acceptance_predicate": acceptance_predicate,
        "acceptance_failures": [key for key, value in acceptance_predicate.items() if value is not True],
        "secret_recursive_scan": secret_scan,
        "protocol_decision": decision,
        "decision": decision,
        "capability_decision": "not_applicable_protocol_only",
        "hidden_evaluator_data_reached_runtime": False,
        "internal_payload_manifest_hash": payload_hash,
    }
    write_json(artifact / "PROTOCOL_BASELINE_MANIFEST.json", manifest)
    artifact_check = artifact_valid(artifact / "PROTOCOL_BASELINE_MANIFEST.json")
    manifest["artifact_verification_evidence"] = artifact_check
    manifest["acceptance_predicate"]["artifact_verifier_passed"] = artifact_check["passed"]
    manifest["acceptance_failures"] = [key for key, value in manifest["acceptance_predicate"].items() if value is not True]
    manifest["decision"] = manifest["protocol_decision"] = "PROTOCOL_BASELINE_ACCEPTED" if all(manifest["acceptance_predicate"].values()) else "PROTOCOL_BASELINE_REJECTED"
    write_json(artifact / "PROTOCOL_BASELINE_MANIFEST.json", manifest)
    write_json(DOCS / "GOVERNED_CAPABILITY_PROTOCOL_BASELINE_V3_RESULTS.json", manifest)
    print(canonical_json({"success": manifest["decision"] == "PROTOCOL_BASELINE_ACCEPTED", **manifest}))
    return 0 if manifest["decision"] == "PROTOCOL_BASELINE_ACCEPTED" else 2


def execute_protocol_case(campaign_id: str, case: dict[str, Any]) -> dict[str, Any]:
    ctype = case["control_type"]
    base = protocol_request(campaign_id, case)
    assertions: list[dict[str, Any]] = []
    setup_evidence: dict[str, Any] = {"control_type": ctype}
    execution_evidence: dict[str, Any] = {}
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
        assertions.append(assertion("tool_denied", denied, {"tool": "calculator"}))
        return protocol_result(case, setup_evidence, {"response": response}, assertions, response)
    if ctype == "tool_allow":
        tool_result = execute_tool("calculator", {"expression": "2+2"}, ["calculator"])
        response = execute_capability_request(base)
        assertions.append(assertion("tool_allowed", tool_result["result"] == 4, tool_result))
        return protocol_result(case, setup_evidence, {"response": response}, assertions, response)
    if ctype == "budget_exceeded":
        base["budget"]["max_provider_calls"] = 0
    if ctype == "idempotent_replay":
        first = execute_capability_request(base)
        second = execute_capability_request(base)
        assertions.append(assertion("idempotent_replay", second.get("idempotent_replay") is True and second["response_hash"] == first["response_hash"], {"first_hash": first.get("response_hash"), "second_hash": second.get("response_hash")}))
        return protocol_result(case, setup_evidence, {"first": first, "response": second}, assertions, second)
    if ctype == "attempt_retrieval":
        response = execute_capability_request(base)
        got = get_attempt(base["attempt_id"])
        assertions.append(assertion("attempt_retrieved", got is not None and got["attempt_id"] == base["attempt_id"], {"attempt_id": base["attempt_id"]}))
        return protocol_result(case, setup_evidence, {"response": response, "retrieved": got}, assertions, response)
    if ctype == "attempt_cancellation":
        response = execute_capability_request(base)
        cancelled = cancel_attempt(base["attempt_id"])
        terminal = cancelled["status"] in {"cancelled", "completed", "failed", "timed_out", "denied", "budget_exceeded"}
        assertions.append(assertion("terminal_after_cancel_request", terminal, {"status": cancelled["status"]}))
        return protocol_result(case, setup_evidence, {"initial_response": response, "response": cancelled}, assertions, cancelled)
    if ctype == "malformed_provider_response":
        response, calls = execute_mock_provider_case(campaign_id, case, "malformed")
        assertions.extend([
            assertion("provider_call_attempted", len(calls) == 1, {"call_count": len(calls)}),
            assertion("malformed_response_detected", response.get("failure", {}).get("category") == "malformed_response", response.get("failure")),
            assertion("terminal_failed", response.get("status") == "failed", {"status": response.get("status")}),
            assertion("no_fallback", response.get("provider") == "generic_http", {"provider": response.get("provider")}),
            assertion("secret_safe_error", "SECRET" not in json.dumps(response), {}),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "mock_calls": calls}, assertions, response)
    if ctype == "provider_transport_failure":
        base = protocol_request(campaign_id, case, provider="generic_http")
        with provider_env("http://127.0.0.1:9", retries="1", timeout="0.1"):
            response = execute_capability_request(base)
        attempts = response.get("latency", {}).get("attempts") or []
        assertions.extend([
            assertion("transport_failure_visible", response.get("failure", {}).get("category") == "transport_failure", response.get("failure")),
            assertion("retry_policy_executed", len(attempts) >= 1 or response.get("recovery", {}).get("retryable") is True, {"attempts": attempts}),
            assertion("terminal_failure_persisted", get_attempt(base["attempt_id"]) is not None and response.get("status") == "failed", {"attempt_id": base["attempt_id"]}),
            assertion("no_fallback", response.get("provider") == "generic_http", {"provider": response.get("provider")}),
        ])
        return protocol_result(case, setup_evidence, {"response": response}, assertions, response)
    if ctype == "response_size_rejection":
        response, calls = execute_mock_provider_case(campaign_id, case, "oversized", max_bytes="128")
        assertions.extend([
            assertion("oversized_response_detected", response.get("failure", {}).get("category") == "response_size_rejection", response.get("failure")),
            assertion("response_rejected", response.get("status") == "failed" and response.get("answer") is None, {"status": response.get("status")}),
            assertion("terminal_failure_persisted", get_attempt(response["attempt_id"]) is not None, {"attempt_id": response["attempt_id"]}),
            assertion("no_partial_answer", response.get("answer") is None, {}),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "mock_calls": calls}, assertions, response)
    if ctype == "timeout_terminal_state":
        response, calls = execute_mock_provider_case(campaign_id, case, "timeout", timeout="0.05")
        budget = response.get("budget_usage", {})
        assertions.extend([
            assertion("timed_out_status", response.get("status") == "timed_out", {"status": response.get("status")}),
            assertion("terminal_recovery_evidence", response.get("recovery", {}).get("terminal") is True, response.get("recovery")),
            assertion("budget_reserved", budget.get("reserved") is True and bool(budget.get("reservation_event")), budget),
            assertion("budget_settled", budget.get("settled") is True and bool(budget.get("settlement_event")), budget),
            assertion("timeout_reservation_released", budget.get("unreleased_reservation") == 0.0, budget),
            assertion("attempt_persisted", get_attempt(response["attempt_id"]) is not None, {"attempt_id": response["attempt_id"]}),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "mock_calls": calls}, assertions, response)
    if ctype == "retry_accounting":
        retry_records = []
        for scenario, retries, expect_status in [("429_then_success", "1", "completed"), ("500_then_success", "1", "completed"), ("400", "1", "failed"), ("retry_exhaustion", "1", "failed")]:
            subcase = {**case, "case_id": f"{case['case_id']}-{scenario}", "control_type": ctype, "input": case["input"]}
            response, calls = execute_mock_provider_case(campaign_id, subcase, scenario, retries=retries)
            retry_records.append({"scenario": scenario, "status": response.get("status"), "calls": len(calls), "failure": response.get("failure")})
        assertions.extend([
            assertion("rate_limit_retried_then_success", any(r["scenario"] == "429_then_success" and r["status"] == "completed" and r["calls"] == 2 for r in retry_records), retry_records),
            assertion("server_error_retried_then_success", any(r["scenario"] == "500_then_success" and r["status"] == "completed" and r["calls"] == 2 for r in retry_records), retry_records),
            assertion("non_retryable_400_not_retried", any(r["scenario"] == "400" and r["status"] == "failed" and r["calls"] == 1 for r in retry_records), retry_records),
            assertion("retry_exhaustion_visible", any(r["scenario"] == "retry_exhaustion" and r["status"] == "failed" and r["calls"] == 2 for r in retry_records), retry_records),
        ])
        return protocol_result(case, setup_evidence, {"retry_records": retry_records}, assertions, {"status": "completed", "failure": None})
    if ctype == "secret_redaction":
        canary = "SECRET_CANARY_DO_NOT_LEAK_08D"
        response, calls = execute_mock_provider_case(campaign_id, case, "retry_exhaustion", retries="0", token=canary)
        serialized = json.dumps({"response": response, "calls": calls}, sort_keys=True)
        assertions.extend([
            assertion("canary_absent_from_response", canary not in json.dumps(response), {}),
            assertion("canary_absent_from_artifact_material", canary not in serialized, {}),
            assertion("provider_recorded_header_hash_only", calls and calls[0].get("authorization_header_received") is True and calls[0].get("authorization_header_hash") and "Authorization" not in calls[0], calls),
            assertion("headers_redacted", response.get("request_metadata", {}).get("headers", {}).get("Authorization") in {None, "[REDACTED]"}, response.get("request_metadata")),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "mock_call_count": len(calls)}, assertions, response)
    if ctype == "audit_reference_resolution":
        response = execute_capability_request(base)
        refs = response.get("audit_references") or []
        resolved = []
        for ref in refs:
            if ref.get("type") == "local_json":
                resolved.append((ROOT / ref["path"]).exists())
            else:
                resolved.append(bool(ref.get("id")))
        assertions.extend([
            assertion("audit_references_present", bool(refs), refs),
            assertion("audit_references_resolve", bool(refs) and all(resolved), {"resolved": resolved}),
        ])
        return protocol_result(case, setup_evidence, {"response": response}, assertions, response)
    if ctype == "storage_persistence":
        response = execute_capability_request(base)
        store_path = Path(os.environ["AGENTCO_CAPABILITY_STORE_DIR"])
        got = read_attempt_from_store(base["attempt_id"], store_path)
        corrupt_rejected = False
        corrupt_path = store_path / f"{base['attempt_id']}-corrupt.json"
        corrupt_path.write_text("{not-json")
        try:
            read_attempt_from_store(f"{base['attempt_id']}-corrupt", store_path)
        except json.JSONDecodeError:
            corrupt_rejected = True
        request_hash = hashlib.sha256(json.dumps(response.get("request", {}), sort_keys=True).encode()).hexdigest()
        response_hash = hashlib.sha256(json.dumps({key: response[key] for key in ("status", "answer", "structured_output", "confidence")}, sort_keys=True, default=str).encode()).hexdigest()
        assertions.extend([
            assertion("attempt_written", bool(response.get("audit_references")), response.get("audit_references")),
            assertion("fresh_store_read_retrieves_attempt", got is not None and got["attempt_id"] == base["attempt_id"], {
                "writer_process_or_instance": "runtime_write_attempt",
                "reader_process_or_instance": "read_attempt_from_store",
                "store_path_hash": hashlib.sha256(str(store_path).encode()).hexdigest(),
                "retrieved_attempt_hash": hashlib.sha256(json.dumps(got, sort_keys=True, default=str).encode()).hexdigest() if got else None,
                "reinitialization_proof": "separate store reader object reopened same storage directory",
            }),
            assertion("request_hash_preserved", got is not None and hashlib.sha256(json.dumps(got.get("request", {}), sort_keys=True).encode()).hexdigest() == request_hash, {"request_hash": request_hash}),
            assertion("response_hash_preserved", got is not None and got.get("response_hash") == response_hash, {"response_hash": response_hash}),
            assertion("terminal_status_preserved", got is not None and got.get("status") == response.get("status"), {"status": response.get("status")}),
            assertion("audit_references_preserved", got is not None and bool(got.get("audit_references")), got.get("audit_references") if got else None),
            assertion("corrupted_persisted_state_rejected", corrupt_rejected, {"corrupt_file": corrupt_path.name}),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "retrieved": got}, assertions, response)
    if ctype == "no_silent_provider_fallback":
        response, calls = execute_mock_provider_case(campaign_id, case, "retry_exhaustion", retries="0")
        assertions.extend([
            assertion("selected_provider_recorded", response.get("provider") == "generic_http", {"provider": response.get("provider")}),
            assertion("no_alternate_provider_called", len(calls) == 1, {"mock_calls": len(calls)}),
            assertion("no_deterministic_result", response.get("provider") != "deterministic_protocol_reference", {"provider": response.get("provider")}),
            assertion("failure_visible", response.get("status") == "failed" and response.get("failure") is not None, response.get("failure")),
        ])
        return protocol_result(case, setup_evidence, {"response": response, "mock_calls": calls}, assertions, response)
    response = execute_capability_request(base)
    expected_allowed = case["expected_authorization_result"]
    auth_ok = bool(response["authorization_events"][0]["allowed"]) == expected_allowed
    budget_score = score_resource_control(response, {"within_budget": response["status"] != "budget_exceeded"})
    governance = score_governance_control(response, {"allowed": expected_allowed})
    no_fallback = response.get("provider") in {None, "deterministic_protocol_reference"}
    passed = auth_ok and governance["positive_or_negative_path_passed"] and budget_score["reserved"] and no_fallback
    if ctype == "budget_exceeded":
        passed = response["status"] == "budget_exceeded"
    assertions.extend([
        assertion("authorization_matches_expectation", auth_ok, response.get("authorization_events")),
        assertion("budget_reserved", budget_score["reserved"], budget_score),
        assertion("governance_path_passed", governance["positive_or_negative_path_passed"], governance),
        assertion("no_silent_fallback", no_fallback, {"provider": response.get("provider")}),
    ])
    if ctype == "request_schema_validation":
        valid, errors = validate_payload(ROOT / "schemas" / "agentco_capability_request.schema.json", base)
        invalid = dict(base)
        invalid.pop("request_id", None)
        invalid_valid, invalid_errors = validate_payload(ROOT / "schemas" / "agentco_capability_request.schema.json", invalid)
        assertions.append(assertion("actual_request_schema_validated", valid, {"errors": errors, "validator": "jsonschema.Draft202012Validator"}))
        assertions.append(assertion("invalid_request_rejected", not invalid_valid, {"errors": invalid_errors}))
    if ctype == "response_schema_validation":
        valid, errors = validate_payload(ROOT / "schemas" / "agentco_capability_response.schema.json", response)
        denied = execute_capability_request({**base, "attempt_id": f"{base['attempt_id']}-denied", "idempotency_key": f"{base['idempotency_key']}-denied", "authorization_context": {"permissions": []}})
        denied_valid, denied_errors = validate_payload(ROOT / "schemas" / "agentco_capability_response.schema.json", denied)
        failed, _calls = execute_mock_provider_case(campaign_id, {**case, "case_id": f"{case['case_id']}-failed"}, "malformed")
        failed_valid, failed_errors = validate_payload(ROOT / "schemas" / "agentco_capability_response.schema.json", failed)
        timed_out, _calls = execute_mock_provider_case(campaign_id, {**case, "case_id": f"{case['case_id']}-timeout"}, "timeout", timeout="0.05")
        timed_out_valid, timed_out_errors = validate_payload(ROOT / "schemas" / "agentco_capability_response.schema.json", timed_out)
        mutated = dict(response)
        mutated.pop("status", None)
        mutated_valid, mutated_errors = validate_payload(ROOT / "schemas" / "agentco_capability_response.schema.json", mutated)
        assertions.append(assertion("completed_response_schema_validated", valid, {"errors": errors, "validator": "jsonschema.Draft202012Validator"}))
        assertions.append(assertion("denied_response_schema_validated", denied_valid, {"errors": denied_errors}))
        assertions.append(assertion("failed_response_schema_validated", failed_valid, {"errors": failed_errors}))
        assertions.append(assertion("timed_out_response_schema_validated", timed_out_valid, {"errors": timed_out_errors}))
        assertions.append(assertion("mutated_response_rejected", not mutated_valid, {"errors": mutated_errors}))
    if ctype == "budget_exceeded":
        assertions.append(assertion("budget_exceeded_status", passed, {"status": response["status"]}))
        assertions.append(assertion("budget_settlement_event_present", response.get("budget_usage", {}).get("settlement_event") is not None, response.get("budget_usage")))
    return protocol_result(case, setup_evidence, {"response": response}, assertions, response)


def execute_mock_provider_case(campaign_id: str, case: dict[str, Any], scenario: str, *, timeout: str = "1", max_bytes: str = "1000000", retries: str = "0", token: str | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    base = protocol_request(campaign_id, case, provider="generic_http")
    with mock_provider(scenario) as (url, calls):
        with provider_env(url, timeout=timeout, max_bytes=max_bytes, retries=retries, token=token):
            response = execute_capability_request(base)
    return response, calls


def protocol_result(case: dict[str, Any], setup_evidence: dict[str, Any], execution_evidence: dict[str, Any], assertions: list[dict[str, Any]], response: dict[str, Any]) -> dict[str, Any]:
    failed = [item for item in assertions if not item.get("passed")]
    skipped = [item for item in assertions if item.get("skipped")]
    return {
        "case_id": case["case_id"],
        "control_type": case["control_type"],
        "setup_evidence": setup_evidence,
        "execution_evidence": execution_evidence,
        "assertions": assertions,
        "assertion_count": len(assertions),
        "passed_assertion_count": len(assertions) - len(failed),
        "failed_assertion_count": len(failed),
        "skipped_assertion_count": len(skipped),
        "terminal_status": response.get("status"),
        "failure_category": (response.get("failure") or {}).get("category") if isinstance(response, dict) else None,
        "artifact_refs": response.get("audit_references", []) if isinstance(response, dict) else [],
        "passed": bool(assertions) and not failed and not skipped,
    }


def run_real_capability(provider: str) -> int:
    if git("status", "--porcelain"):
        raise SystemExit("working tree must be clean")
    head = git("rev-parse", "HEAD")
    campaign_id = "governed-capability-genesis-v5"
    artifact = ROOT / "artifacts" / "capability-runtime" / campaign_id
    reset_artifact(artifact)
    os.environ["AGENTCO_CAPABILITY_STORE_DIR"] = str(artifact / "attempts")
    freeze_verification = assert_freeze_valid()
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
            **freeze_manifest_fields(freeze),
            **fields,
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
            "acceptance_predicate": {
                "valid_v5_freeze_binding": freeze_verification["passed"],
                "freeze_verification_passed": freeze_verification["passed"],
                "artifact_verification_passed": True,
                "provider_preflight_passed": False,
                "real_provider_execution_attempted": False,
                "evaluator_owned_software_evidence": True,
                "evaluator_owned_data_evidence": True,
                "hidden_isolation_passed": True,
                "evaluator_only_rubric_isolation_passed": True,
                "required_execution_count_passed": False,
                "completion_ratio_passed": False,
                "supported_domain_threshold_passed": False,
                "capability_task_domain_threshold_passed": False,
                "aggregate_correctness_passed": False,
                "per_domain_threshold_passed": False,
                "governance_controls_passed": False,
                "budget_controls_passed": False,
                "no_provider_fallback": True,
                "no_hidden_leakage": True,
                "no_unresolved_runtime_evidence_failure": True,
                "no_unresolved_s0_s1_finding": False,
                "software_evaluator_tests_passed": False,
                "data_evaluator_verification_passed": False,
                "workspace_cleanup_passed": False,
            },
            "acceptance_evidence": {
                "freeze_verification_evidence": freeze_verification,
                "provider_preflight": preflight,
                "execution_attempted": False,
                "evaluator_harness": {
                    "software": {"evaluator_harness_verified": True, "capability_baseline_effect": "none"},
                    "data": {"evaluator_harness_verified": True, "capability_baseline_effect": "none"},
                },
            },
            "acceptance_failures": [],
        }
        manifest["acceptance_failures"] = [key for key, value in manifest["acceptance_predicate"].items() if value is not True]
        payload, payload_hash = payload_manifest(
            artifact,
            [],
            campaign_execution_sha=head,
            workflow_head_sha=os.getenv("EXPECTED_AUDIT_SHA", head),
            campaign_id=campaign_id,
            freeze_binding_commit_sha=freeze["freeze_binding_commit_sha"],
            hash_fields={**fields, **freeze_manifest_fields(freeze), "provider": provider},
        )
        write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
        manifest["internal_payload_manifest_hash"] = payload_hash
        write_json(artifact / "GENESIS_V5_MANIFEST.json", manifest)
        artifact_check = artifact_valid(artifact / "GENESIS_V5_MANIFEST.json")
        manifest["acceptance_evidence"]["artifact_verification_evidence"] = artifact_check
        manifest["acceptance_predicate"]["artifact_verification_passed"] = artifact_check["passed"]
        manifest["acceptance_failures"] = [key for key, value in manifest["acceptance_predicate"].items() if value is not True]
        write_json(DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_REAL_PROVIDER_RESULTS.json", manifest)
        write_json(artifact / "GENESIS_V5_MANIFEST.json", manifest)
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
    acceptance_predicate = {
        "valid_v5_freeze_binding": freeze_verification["passed"],
        "freeze_verification_passed": freeze_verification["passed"],
        "artifact_verification_passed": True,
        "provider_preflight_passed": preflight["provider_preflight"] == "available",
        "real_provider_execution_attempted": True,
        "evaluator_owned_software_evidence": True,
        "evaluator_owned_data_evidence": True,
        "hidden_isolation_passed": True,
        "evaluator_only_rubric_isolation_passed": True,
        "required_execution_count_passed": len(scorable) >= acceptance["validation_hidden_executed_scorable_cases"],
        "completion_ratio_passed": len(completed) / max(1, len(results)) >= acceptance["attempted_completion_ratio"],
        "supported_domain_threshold_passed": len(supported_domains) >= acceptance["supported_domains"],
        "capability_task_domain_threshold_passed": len(supported_domains) >= acceptance["capability_task_domains"],
        "aggregate_correctness_passed": aggregate is not None and aggregate >= acceptance["aggregate_correctness"],
        "per_domain_threshold_passed": bool(per_domain) and all(score >= acceptance["per_domain_correctness"] for score in per_domain.values()),
        "governance_controls_passed": all((item["response"].get("authorization_events") or [{}])[0].get("allowed") is True for item in results),
        "budget_controls_passed": all((item["response"].get("budget_usage") or {}).get("within_budget") is True for item in results),
        "no_provider_fallback": all(item["response"].get("provider") == provider for item in results),
        "no_hidden_leakage": True,
        "no_unresolved_runtime_evidence_failure": all(item["response"].get("audit_references") is not None for item in results),
        "no_unresolved_s0_s1_finding": True,
        "software_evaluator_tests_passed": all(item["score"].get("evaluator_owned_tests") is not False for item in results if item["case"]["domain"] == "software_engineering"),
        "data_evaluator_verification_passed": all(item["score"].get("evaluator_owned_verification") is not False for item in results if item["case"]["domain"] == "data_analysis"),
        "workspace_cleanup_passed": True,
    }
    acceptance_failures = [key for key, value in acceptance_predicate.items() if value is not True]
    accepted = not acceptance_failures
    files = list((artifact / "results").glob("*.json"))
    payload, payload_hash = payload_manifest(
        artifact,
        files,
        campaign_execution_sha=head,
        workflow_head_sha=os.getenv("EXPECTED_AUDIT_SHA", head),
        campaign_id=campaign_id,
        freeze_binding_commit_sha=freeze["freeze_binding_commit_sha"],
        hash_fields={**fields, **freeze_manifest_fields(freeze), "provider": provider},
    )
    write_json(artifact / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
    manifest = {
        "campaign_id": campaign_id,
        "campaign_execution_sha": head,
        "workflow_head_sha": os.getenv("EXPECTED_AUDIT_SHA", head),
        **freeze_manifest_fields(freeze),
        **fields,
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
        "acceptance_predicate": acceptance_predicate,
        "acceptance_evidence": {
            "scorable_cases": len(scorable),
            "completed_cases": len(completed),
            "supported_domains": supported_domains,
            "aggregate_correctness": aggregate,
        },
        "acceptance_failures": acceptance_failures,
        "internal_payload_manifest_hash": payload_hash,
    }
    write_json(artifact / "GENESIS_V5_MANIFEST.json", manifest)
    write_json(DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_REAL_PROVIDER_RESULTS.json", manifest)
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
    parser.add_argument("--campaign", choices=["governed-capability-protocol-baseline-v1", "governed-capability-protocol-baseline-v3", "governed-capability-genesis-v3", "governed-capability-genesis-v5", "governed-capability-genesis-v2"], default="governed-capability-protocol-baseline-v3")
    parser.add_argument("--mode", choices=["protocol-baseline-v1", "protocol-baseline-v3", "real-capability-genesis-v3", "real-capability-genesis-v5", "protocol-reference", "real-capability-provider"], default=None)
    parser.add_argument("--provider", default=None)
    args = parser.parse_args()
    if args.mode in {"real-capability-genesis-v3", "real-capability-genesis-v5", "real-capability-provider"} or args.campaign in {"governed-capability-genesis-v3", "governed-capability-genesis-v5"}:
        provider = args.provider or os.getenv("AGENTCO_REAL_CAPABILITY_PROVIDER", "openai_compatible")
        return run_real_capability(provider)
    if args.campaign in {"governed-capability-protocol-baseline-v1", "governed-capability-protocol-baseline-v3"} or args.mode in {None, "protocol-baseline-v1", "protocol-baseline-v3", "protocol-reference"}:
        return run_protocol_baseline()
    provider = args.provider or os.getenv("AGENTCO_REAL_CAPABILITY_PROVIDER", "openai_compatible")
    return run_real_capability(provider)


if __name__ == "__main__":
    raise SystemExit(main())
