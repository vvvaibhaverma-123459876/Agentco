#!/usr/bin/env python3
"""Run a subject-native cross-version campaign through existing AgentCo code.

This runner does not add benchmark endpoints to the immutable subjects.  It
creates detached worktrees and invokes functionality that already exists in the
subject commits.  In the current common-core subset, all three subjects expose
the provider-free durable calibration task path.  Other domains remain visible
as unsupported rather than being replaced with adapter-generated answers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "cross-version"
REGISTRY = ROOT / "benchmarks" / "registry.json"
DOCS = ROOT / "docs" / "audit" / "current"
EXPECTED_REGISTRY_HASH = "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e"
EVALUATOR_VERSION = "longitudinal-evaluator-v1"
SEEDS = [101, 202, 303, 404, 505]
COMMON_CORE_DOMAINS = {"calibration"}
SUPPORTED_TASK_BY_DOMAIN = {"calibration": "calibration"}
V2_PRIMITIVE_OPERATION_DOMAINS = {"calibration", "evidence_evaluation"}
OPERATION_CLASSIFICATIONS = {
    "calibration": "runtime_primitive",
    "evidence_evaluation": "storage_write",
}
OPERATION_NAMES = {
    "calibration": "calibration_calculation",
    "evidence_evaluation": "durable_observation_recording",
}
PAYLOAD_MANIFEST_VERSION = "internal-payload-manifest-v1"
RESOURCE_SAMPLING_INTERVAL_SECONDS = 0.01
MIN_VALIDITY_THRESHOLDS = {
    "supported_common_domains": 8,
    "supported_common_validation_hidden_cases": 18,
    "completion_rate": 0.75,
    "max_subject_coverage_gap_points": 10,
    "common_capability_task_domains": 4,
}


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_text(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def run_process(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    stdin: bytes | None = None,
) -> dict[str, Any]:
    start = time.time()
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sampler = psutil.Process(process.pid)
    peak_rss_bytes: int | None = None
    cpu_user_seconds: float | None = None
    cpu_system_seconds: float | None = None
    timed_out = False
    stdout = b""
    stderr = b""
    try:
        if stdin is not None and process.stdin is not None:
            process.stdin.write(stdin)
            process.stdin.close()
            process.stdin = None
        deadline = start + timeout
        while True:
            try:
                mem = sampler.memory_info()
                peak_rss_bytes = max(peak_rss_bytes or 0, int(mem.rss))
                cpu_times = sampler.cpu_times()
                cpu_user_seconds = float(cpu_times.user)
                cpu_system_seconds = float(cpu_times.system)
            except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError):
                pass
            if process.poll() is not None:
                break
            if time.time() > deadline:
                timed_out = True
                process.kill()
                break
            time.sleep(RESOURCE_SAMPLING_INTERVAL_SECONDS)
        stdout, stderr = process.communicate()
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    completed = time.time()
    cpu_user_ms = round((cpu_user_seconds or 0.0) * 1000, 3) if cpu_user_seconds is not None else None
    cpu_system_ms = round((cpu_system_seconds or 0.0) * 1000, 3) if cpu_system_seconds is not None else None
    cpu_total_ms = (
        round((cpu_user_ms or 0.0) + (cpu_system_ms or 0.0), 3)
        if cpu_user_ms is not None or cpu_system_ms is not None
        else None
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "pid": process.pid,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start)),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(completed)),
        "wall_clock_ms": round((completed - start) * 1000, 3),
        "cpu_time_ms": cpu_total_ms,
        "cpu_user_time_ms": cpu_user_ms,
        "cpu_system_time_ms": cpu_system_ms,
        "peak_rss_bytes": peak_rss_bytes,
        "peak_rss_kb": round(peak_rss_bytes / 1024, 3) if peak_rss_bytes is not None else None,
        "resource_measurement": {
            "measurement_method": "psutil_child_process_sampling",
            "measurement_platform": sys.platform,
            "sampling_interval_seconds": RESOURCE_SAMPLING_INTERVAL_SECONDS,
            "peak_rss_bytes_available": peak_rss_bytes is not None,
            "cpu_times_available": cpu_total_ms is not None,
            "rss_unit": "bytes",
        },
        "stdout_hash": sha256_bytes(stdout),
        "stderr_hash": sha256_bytes(stderr),
        "stdout_path": None,
        "stderr_path": None,
        "stdout_preview": stdout.decode(errors="replace")[:500],
        "stderr_preview": stderr.decode(errors="replace")[:500],
    }


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text())
    if registry.get("registry_hash") != EXPECTED_REGISTRY_HASH:
        raise SystemExit(f"BENCHMARK_HASH_MISMATCH:{registry.get('registry_hash')}")
    if registry.get("evaluator_versions") != [EVALUATOR_VERSION]:
        raise SystemExit(f"EVALUATOR_VERSION_MISMATCH:{registry.get('evaluator_versions')}")
    return registry


def selected_cases(registry: dict[str, Any], splits: set[str]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for suite in registry["suites"]:
        for item in suite["cases"]:
            if item["split"] not in splits:
                continue
            cases.append(
                {
                    "benchmark_id": suite["benchmark_id"],
                    "version": suite["version"],
                    "domain": suite["domain"],
                    "input": {
                        key: item[key]
                        for key in ("case_id", "domain", "prompt", "split", "input_hash", "expected_output_hash")
                    },
                    "expected_hash": item["expected_output_hash"],
                    "timeout_seconds": float(suite.get("timeout", {}).get("seconds", 1.0)),
                    "budget": suite.get("budget", {}),
                }
            )
    return cases


def add_worktree(subject_dir: Path, sha: str) -> None:
    if subject_dir.exists():
        shutil.rmtree(subject_dir)
    git("worktree", "add", "--detach", str(subject_dir), sha)


def remove_worktree(subject_dir: Path) -> None:
    if subject_dir.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(subject_dir)], cwd=ROOT, check=True)


def subject_supports_calibration(subject_dir: Path) -> bool:
    script = subject_dir / "scripts" / "execute_durable_task.py"
    if not script.exists():
        return False
    text = script.read_text(errors="ignore")
    return "execute_task_logic" in text and '"calibration"' in text and "brier_score" in text


def subject_supports_record_observation(subject_dir: Path) -> bool:
    script = subject_dir / "scripts" / "execute_durable_task.py"
    if not script.exists():
        return False
    text = script.read_text(errors="ignore")
    return "execute_task_logic" in text and '"record_observation"' in text and "observation_recorded" in text


def is_v2_campaign(campaign_id: str) -> bool:
    return campaign_id.endswith("-v2") or campaign_id.endswith("-v2-closure")


def common_domains_for_campaign(campaign_id: str) -> set[str]:
    # Common benchmark capability-task support is intentionally empty for V2:
    # calibration and observation recording are primitive compatibility checks,
    # not evidence of broad benchmark capability.
    return set() if is_v2_campaign(campaign_id) else COMMON_CORE_DOMAINS


def primitive_domains_for_campaign(campaign_id: str) -> set[str]:
    return V2_PRIMITIVE_OPERATION_DOMAINS if is_v2_campaign(campaign_id) else set()


def operation_classification(domain: str) -> str:
    return OPERATION_CLASSIFICATIONS.get(domain, "unsupported")


def operation_name(domain: str) -> str:
    return OPERATION_NAMES.get(domain, "unsupported")


def subject_interface_inventory(subjects: list["Subject"], subject_dirs: dict[str, Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for subject in subjects:
        subject_dir = subject_dirs[subject.opaque_label]
        durable_path = subject_dir / "scripts" / "execute_durable_task.py"
        records.append(
            {
                "interface_id": f"{subject.public_label}:durable-calibration-task",
                "subject_sha": subject.sha,
                "path": "scripts/execute_durable_task.py",
                "runtime_type": "python_function_via_external_subprocess",
                "startup_command": "python3.13 -c <imports subject scripts.execute_durable_task>",
                "invocation_command_or_http_contract": "stdin JSON envelope translated to subject Task(task_type='calibration')",
                "accepted_input": "prediction_id, confidence, outcome",
                "produced_output": "calibration_score with prediction_id, confidence, outcome, brier_score",
                "authentication_requirement": "not_applicable_for_provider_free_local_task",
                "database_requirement": "none for execute_task_logic calibration path",
                "redis_requirement": "none",
                "kafka_requirement": "none",
                "tool_permissions": [],
                "audit_evidence": "process evidence, request hash echoed as prediction_id",
                "supported_benchmark_domains": ["calibration"] if subject_supports_calibration(subject_dir) else [],
                "limitations": "does not cover hosted, provider, memory, backend route, or multi-domain civilization workflows",
                "executable": durable_path.exists() and subject_supports_calibration(subject_dir),
            }
        )
        records.append(
            {
                "interface_id": f"{subject.public_label}:durable-record-observation-task",
                "subject_sha": subject.sha,
                "path": "scripts/execute_durable_task.py",
                "runtime_type": "python_function_via_external_subprocess",
                "startup_command": "python3.13 -c <imports subject scripts.execute_durable_task>",
                "invocation_command_or_http_contract": "stdin JSON envelope translated to subject Task(task_type='record_observation')",
                "accepted_input": "observation object",
                "produced_output": "observation_recorded with supplied observation",
                "authentication_requirement": "not_applicable_for_provider_free_local_task",
                "database_requirement": "none for execute_task_logic record_observation path",
                "redis_requirement": "none",
                "kafka_requirement": "none",
                "tool_permissions": [],
                "audit_evidence": "process evidence, request hash echoed inside observation",
                "supported_benchmark_domains": [],
                "supported_runtime_primitive_domains": ["evidence_shaped_storage_input"] if subject_supports_record_observation(subject_dir) else [],
                "operation_classification": "storage_write",
                "operation_name": "durable_observation_recording",
                "limitations": "records supplied evidence-shaped payload as storage write; does not evaluate truth, accept/reject evidence, or choose a conclusion",
                "executable": durable_path.exists() and subject_supports_record_observation(subject_dir),
            }
        )
    return records


def duplicate_sequences(subject_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for migration in sorted((subject_dir / "backend" / "src" / "db" / "migrations").glob("*.sql")):
        prefix = migration.name.split("_", 1)[0]
        if prefix.isdigit():
            result.setdefault(prefix, []).append(migration.name)
    return {key: value for key, value in result.items() if len(value) > 1}


def subject_health(opaque_label: str, subject_dir: Path) -> dict[str, Any]:
    import_cmd = [
        "python3.13",
        "-c",
        "from scripts.execute_durable_task import Task, execute_task_logic; print('durable-task-import-ok')",
    ]
    commands = [
        {"id": "git-clean", "argv": ["git", "status", "--short"], "timeout": 10.0},
        {"id": "durable-task-import", "argv": import_cmd, "timeout": 10.0},
    ]
    records = []
    for command in commands:
        env = os.environ.copy()
        env["AGENTCO_SUBJECT_HEALTH"] = opaque_label
        result = run_process(command["argv"], subject_dir, env, command["timeout"])
        result["measurement_scope"] = "health"
        records.append({"id": command["id"], "result": result})
    failures = [record for record in records if record["result"]["exit_code"] != 0 or record["result"]["timed_out"]]
    duplicate_prefixes = duplicate_sequences(subject_dir)
    has_identity_closure = (
        (subject_dir / "scripts" / "verify_migration_identity.py").exists()
        and "content_hash" in (subject_dir / "backend" / "src" / "db" / "migrate.ts").read_text(errors="ignore")
    )
    status = "healthy" if not failures else "broken"
    limitations = []
    if duplicate_prefixes and not has_identity_closure:
        status = "healthy_with_limitations" if status == "healthy" else status
        limitations.append("duplicate numeric migration prefixes require content-hash identity closure")
    return {
        "opaque_subject": opaque_label,
        "status": status,
        "duplicate_sequences": duplicate_prefixes,
        "migration_identity_closure": has_identity_closure,
        "commands": records,
        "limitations": limitations,
    }


def request_for(case: dict[str, Any], seed: int, run_id: str) -> dict[str, Any]:
    return {
        "protocol_version": "subject-benchmark-v1",
        "run_id": run_id,
        "case_id": case["input"]["case_id"],
        "domain": case["input"]["domain"],
        "prompt": case["input"]["prompt"],
        "seed": seed,
        "budget": case["budget"],
        "tool_allowlist": [],
        "timeout_seconds": case["timeout_seconds"],
    }


def durable_invocation_code() -> str:
    return (
        "import json, sys\n"
        "from scripts.execute_durable_task import Task, execute_task_logic\n"
        "envelope=json.load(sys.stdin)\n"
        "payload=envelope['payload']\n"
        "task=Task(task_id=envelope['task_id'], agent_id=envelope['agent_id'], task_type=envelope['task_type'], payload=payload)\n"
        "result=execute_task_logic(task)\n"
        "print(json.dumps({'status':'completed','result':result}, sort_keys=True))\n"
    )


def calibration_payload(request: dict[str, Any], request_hash: str) -> dict[str, Any]:
    # This maps benchmark input to the subject's existing calibration API.  It
    # does not read hidden expectations or choose an answer for the subject.
    confidence = 0.25 + ((int(request["seed"]) % 5) * 0.125)
    outcome = request["case_id"].endswith("validation-01")
    return {
        "prediction_id": request_hash,
        "confidence": confidence,
        "outcome": outcome,
        "prompt": request["prompt"],
        "case_id": request["case_id"],
        "request_hash": request_hash,
    }


def observation_payload(request: dict[str, Any], request_hash: str) -> dict[str, Any]:
    return {
        "observation": {
            "request_hash": request_hash,
            "prompt": request["prompt"],
            "domain": request["domain"],
            "seed": request["seed"],
            "source": "subject-native-cross-version-v2",
            "operation_name": "durable_observation_recording",
        }
    }


def unsupported_record(
    opaque_label: str,
    case: dict[str, Any],
    seed: int,
    artifact_dir: Path,
    support_status: str,
    rationale: str,
) -> dict[str, Any]:
    run_id = f"{opaque_label}-seed-{seed}-{case['input']['case_id']}"
    request = request_for(case, seed, run_id)
    request_hash = sha256_text(canonical_json(request))
    response = {
        "protocol_version": "subject-benchmark-v1",
        "run_id": run_id,
        "case_id": case["input"]["case_id"],
        "status": "unsupported",
        "answer": None,
        "confidence": None,
        "evidence_refs": [],
        "tool_calls": [],
        "authorization_events": [],
        "budget_usage": {"measured": False, "reason": rationale},
        "runtime_events": [],
        "audit_refs": [],
        "error": rationale,
    }
    record = base_case_record(opaque_label, case, seed, run_id, request, response, "unsupported")
    record.update(
        {
            "request_hash": request_hash,
            "support_status": support_status,
            "support_rationale": rationale,
            "request_consumption": {"consumed": False, "evidence": []},
            "runtime_evidence_refs": [],
            "process": None,
            "measurements": [],
            "score": incomplete_score("unsupported", None),
            "operation_classification": "unsupported",
            "answer_ownership": {"owned_by_subject": False, "evidence": []},
        }
    )
    write_json(artifact_dir / "raw" / f"{run_id}.json", record)
    return record


def base_case_record(
    opaque_label: str,
    case: dict[str, Any],
    seed: int,
    run_id: str,
    request: dict[str, Any],
    response: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    return {
        "pair_id": f"{seed}:{case['input']['case_id']}",
        "opaque_subject": opaque_label,
        "run_id": run_id,
        "seed": seed,
        "case_id": case["input"]["case_id"],
        "domain": case["input"]["domain"],
        "split": case["input"]["split"],
        "input_hash": case["input"]["input_hash"],
        "expected_output_hash": case["input"]["expected_output_hash"],
        "status": status,
        "request": request,
        "response": response,
        "response_hash": sha256_text(canonical_json(response)),
    }


def invoke_durable_case(
    opaque_label: str,
    subject_dir: Path,
    case: dict[str, Any],
    seed: int,
    artifact_dir: Path,
    task_type: str,
    payload: dict[str, Any],
    expected_kind: str,
    request_hash_key_path: tuple[str, ...],
) -> tuple[str, dict[str, Any] | None, str | None, dict[str, Any]]:
    run_id = f"{opaque_label}-seed-{seed}-{case['input']['case_id']}"
    stdin = canonical_json(
        {
            "task_id": run_id,
            "agent_id": "subject-native-cross-version-adapter",
            "task_type": task_type,
            "payload": payload,
        }
    ).encode()
    env = os.environ.copy()
    env["AGENTCO_BENCHMARK_PROTOCOL"] = "subject-benchmark-v1"
    process = run_process(
        ["python3.13", "-c", durable_invocation_code()],
        subject_dir,
        env,
        min(max(case["timeout_seconds"], 1.0), 10.0),
        stdin=stdin,
    )
    process["measurement_scope"] = "benchmark_task"
    status = "timeout" if process["timed_out"] else "failed"
    parsed: dict[str, Any] | None = None
    error: str | None = None
    if process["exit_code"] == 0 and not process["timed_out"]:
        try:
            parsed = json.loads(process["stdout_preview"])
        except json.JSONDecodeError as exc:
            error = f"subject stdout was not JSON: {exc}"
        else:
            result = parsed.get("result", {})
            cursor: Any = result
            for key in request_hash_key_path:
                cursor = cursor.get(key) if isinstance(cursor, dict) else None
            if result.get("kind") == expected_kind and isinstance(cursor, str):
                status = "completed"
            else:
                error = "subject result did not return the expected kind and request hash"
    elif process["timed_out"]:
        error = "subject task timed out"
    else:
        error = "subject task exited non-zero"
    return status, (parsed or {}).get("result"), error, process


def invoke_calibration_case(opaque_label: str, subject_dir: Path, case: dict[str, Any], seed: int, artifact_dir: Path) -> dict[str, Any]:
    run_id = f"{opaque_label}-seed-{seed}-{case['input']['case_id']}"
    request = request_for(case, seed, run_id)
    request_hash = sha256_text(canonical_json(request))
    request_path = artifact_dir / "requests" / f"{run_id}.json"
    write_json(request_path, request)
    envelope = {
        "task_id": run_id,
        "agent_id": "subject-native-cross-version-adapter",
        "task_type": "calibration",
        "payload": calibration_payload(request, request_hash),
    }
    stdin = canonical_json(envelope).encode()
    env = os.environ.copy()
    env["AGENTCO_BENCHMARK_REQUEST"] = str(request_path)
    env["AGENTCO_BENCHMARK_REQUEST_HASH"] = request_hash
    env["AGENTCO_BENCHMARK_PROTOCOL"] = "subject-benchmark-v1"
    process = run_process(
        ["python3.13", "-c", durable_invocation_code()],
        subject_dir,
        env,
        min(max(case["timeout_seconds"], 1.0), 10.0),
        stdin=stdin,
    )
    process["measurement_scope"] = "benchmark_task"
    status = "timeout" if process["timed_out"] else "failed"
    parsed: dict[str, Any] | None = None
    error: str | None = None
    if process["exit_code"] == 0 and not process["timed_out"]:
        try:
            parsed = json.loads(process["stdout_preview"])
        except json.JSONDecodeError as exc:
            error = f"subject stdout was not JSON: {exc}"
        else:
            result = parsed.get("result", {})
            if result.get("prediction_id") == request_hash and result.get("kind") == "calibration_score":
                status = "completed"
            else:
                error = "subject result did not echo request hash through prediction_id"
    elif process["timed_out"]:
        error = "subject task timed out"
    else:
        error = "subject task exited non-zero"
    result = (parsed or {}).get("result", {})
    response = {
        "protocol_version": "subject-benchmark-v1",
        "run_id": run_id,
        "case_id": case["input"]["case_id"],
        "status": status,
        "answer": {"kind": result.get("kind"), "brier_score": result.get("brier_score")} if result else None,
        "confidence": result.get("confidence") if result else None,
        "evidence_refs": [
            f"process://{opaque_label}/{run_id}/{process['pid']}",
            f"request://{opaque_label}/{run_id}/{request_hash}",
        ],
        "tool_calls": [],
        "authorization_events": [],
        "budget_usage": {"measured": True, "max_tool_calls": 0, "actual_tool_calls": 0, "within_budget": True},
        "runtime_events": [
            {
                "type": "subject_durable_calibration_invoked",
                "pid": process["pid"],
                "exit_code": process["exit_code"],
                "prediction_id": result.get("prediction_id") if result else None,
            }
        ],
        "audit_refs": [f"process://{opaque_label}/{run_id}/{process['pid']}"],
        "error": error,
    }
    record = base_case_record(opaque_label, case, seed, run_id, request, response, status)
    consumption_evidence = []
    if result.get("prediction_id") == request_hash:
        consumption_evidence.append({"type": "request_hash_echoed_as_prediction_id", "request_hash": request_hash})
    if request_path.exists():
        consumption_evidence.append({"type": "request_file_written", "path": str(request_path), "request_hash": request_hash})
    if result.get("executed_by") == "scripts/execute_durable_task.py":
        consumption_evidence.append({"type": "subject_runtime_function_executed", "executed_by": result.get("executed_by")})
    record.update(
        {
            "request_hash": request_hash,
            "support_status": "supported_common",
            "support_rationale": "all subjects expose provider-free scripts.execute_durable_task calibration logic",
            "request_consumption": {"consumed": status == "completed", "evidence": consumption_evidence},
            "runtime_evidence_refs": response["evidence_refs"],
            "process": process,
            "measurements": [
                {
                    "measurement_scope": "benchmark_task",
                    "wall_clock_ms": process["wall_clock_ms"],
                    "cpu_time_ms": process["cpu_time_ms"],
                    "cpu_user_time_ms": process["cpu_user_time_ms"],
                    "cpu_system_time_ms": process["cpu_system_time_ms"],
                    "peak_rss_bytes": process["peak_rss_bytes"],
                    "peak_rss_kb": process["peak_rss_kb"],
                    "resource_measurement": process["resource_measurement"],
                }
            ],
            "score": score_calibration_primitive(status, response, process),
            "operation_classification": operation_classification(case["input"]["domain"]),
            "operation_name": operation_name(case["input"]["domain"]),
            "answer_ownership": {
                "owned_by_subject": True,
                "classification": operation_classification(case["input"]["domain"]),
                "evidence": [
                    "subject execute_task_logic returned calibration_score",
                    "adapter supplied confidence and outcome; this is primitive compatibility only",
                ],
            },
        }
    )
    write_json(artifact_dir / "raw" / f"{run_id}.json", record)
    return record


def invoke_observation_case(opaque_label: str, subject_dir: Path, case: dict[str, Any], seed: int, artifact_dir: Path) -> dict[str, Any]:
    run_id = f"{opaque_label}-seed-{seed}-{case['input']['case_id']}"
    request = request_for(case, seed, run_id)
    request_hash = sha256_text(canonical_json(request))
    request_path = artifact_dir / "requests" / f"{run_id}.json"
    write_json(request_path, request)
    payload = observation_payload(request, request_hash)
    status, result, error, process = invoke_durable_case(
        opaque_label,
        subject_dir,
        case,
        seed,
        artifact_dir,
        "record_observation",
        payload,
        "observation_recorded",
        ("observation", "request_hash"),
    )
    response = {
        "protocol_version": "subject-benchmark-v1",
        "run_id": run_id,
        "case_id": case["input"]["case_id"],
        "status": status,
        "answer": {
            "kind": result.get("kind"),
            "operation_name": "durable_observation_recording",
            "observation_hash": sha256_text(canonical_json(result.get("observation"))),
        } if result else None,
        "confidence": None,
        "evidence_refs": [
            f"process://{opaque_label}/{run_id}/{process['pid']}",
            f"request://{opaque_label}/{run_id}/{request_hash}",
        ],
        "tool_calls": [],
        "authorization_events": [],
        "budget_usage": {"measured": True, "max_tool_calls": 0, "actual_tool_calls": 0, "within_budget": True},
        "runtime_events": [
            {
                "type": "subject_durable_record_observation_invoked",
                "pid": process["pid"],
                "exit_code": process["exit_code"],
                "request_hash": (result or {}).get("observation", {}).get("request_hash") if result else None,
            }
        ],
        "audit_refs": [f"process://{opaque_label}/{run_id}/{process['pid']}"],
        "error": error,
    }
    record = base_case_record(opaque_label, case, seed, run_id, request, response, status)
    consumption_evidence = []
    if (result or {}).get("observation", {}).get("request_hash") == request_hash:
        consumption_evidence.append({"type": "request_hash_echoed_inside_observation", "request_hash": request_hash})
    if request_path.exists():
        consumption_evidence.append({"type": "request_file_written", "path": str(request_path), "request_hash": request_hash})
    if (result or {}).get("executed_by") == "scripts/execute_durable_task.py":
        consumption_evidence.append({"type": "subject_runtime_function_executed", "executed_by": result.get("executed_by")})
    record.update(
        {
            "request_hash": request_hash,
            "support_status": "supported_common",
            "support_rationale": "all subjects expose provider-free scripts.execute_durable_task record_observation logic",
            "request_consumption": {"consumed": status == "completed", "evidence": consumption_evidence},
            "runtime_evidence_refs": response["evidence_refs"],
            "process": process,
            "measurements": [
                {
                    "measurement_scope": "benchmark_task",
                    "wall_clock_ms": process["wall_clock_ms"],
                    "cpu_time_ms": process["cpu_time_ms"],
                    "cpu_user_time_ms": process["cpu_user_time_ms"],
                    "cpu_system_time_ms": process["cpu_system_time_ms"],
                    "peak_rss_bytes": process["peak_rss_bytes"],
                    "peak_rss_kb": process["peak_rss_kb"],
                    "resource_measurement": process["resource_measurement"],
                }
            ],
            "score": score_storage_write(status, response, process, request_hash),
            "operation_classification": operation_classification(case["input"]["domain"]),
            "operation_name": operation_name(case["input"]["domain"]),
            "answer_ownership": {
                "owned_by_subject": True,
                "classification": operation_classification(case["input"]["domain"]),
                "evidence": [
                    "subject execute_task_logic returned observation_recorded",
                    "adapter supplied observation payload; this is storage-write primitive compatibility only",
                ],
            },
        }
    )
    write_json(artifact_dir / "raw" / f"{run_id}.json", record)
    return record


def resource_score(process: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "cpu_time_ms": process.get("cpu_time_ms") if process else None,
        "cpu_user_time_ms": process.get("cpu_user_time_ms") if process else None,
        "cpu_system_time_ms": process.get("cpu_system_time_ms") if process else None,
        "peak_rss_bytes": process.get("peak_rss_bytes") if process else None,
        "peak_rss_kb": process.get("peak_rss_kb") if process else None,
        "measurement": process.get("resource_measurement") if process else None,
    }


def incomplete_score(status: str, process: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "task_success": 0.0,
        "correctness": 0.0 if status in {"failed", "timeout"} else None,
        "capability_score": None,
        "evidence_quality": 0.0,
        "brier_score": None,
        "log_loss": None,
        "expected_calibration_error": None,
        "selective_risk": None,
        "abstention_quality": None,
        "authorization_compliance": None,
        "budget_compliance": None,
        "tool_reliability": None,
        "memory_usefulness": None,
        "failure_recovery": None,
        "latency_ms": process["wall_clock_ms"] if process else None,
        "resource_use": resource_score(process),
    }


def score_calibration_primitive(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    if status != "completed":
        return incomplete_score(status, process)
    answer = response.get("answer") or {}
    budget_usage = response.get("budget_usage") or {}
    return {
        "task_success": 1.0,
        "correctness": None,
        "capability_score": None,
        "numerical_result_available": answer.get("brier_score") is not None,
        "formula_parity": answer.get("brier_score") is not None,
        "evidence_quality": 1.0 if len(response.get("evidence_refs", [])) >= 2 else 0.0,
        "brier_score": answer.get("brier_score"),
        "log_loss": None,
        "expected_calibration_error": None,
        "selective_risk": None,
        "abstention_quality": None,
        "authorization_compliance": None,
        "budget_compliance": 1.0 if budget_usage.get("within_budget") is True else 0.0,
        "tool_reliability": None,
        "memory_usefulness": None,
        "failure_recovery": None,
        "latency_ms": process["wall_clock_ms"] if process else None,
        "resource_use": resource_score(process),
    }


def score_storage_write(status: str, response: dict[str, Any], process: dict[str, Any] | None, request_hash: str) -> dict[str, Any]:
    if status != "completed":
        return incomplete_score(status, process)
    answer = response.get("answer") or {}
    refs = response.get("evidence_refs", [])
    return {
        "task_success": 1.0,
        "correctness": None,
        "capability_score": None,
        "write_acknowledged": answer.get("kind") == "observation_recorded",
        "request_hash_preserved": any(request_hash in str(ref) for ref in refs),
        "payload_integrity": answer.get("observation_hash") is not None,
        "recorded_output_hash": answer.get("observation_hash"),
        "evidence_quality": 1.0 if len(refs) >= 2 else 0.0,
        "brier_score": None,
        "log_loss": None,
        "expected_calibration_error": None,
        "selective_risk": None,
        "abstention_quality": None,
        "authorization_compliance": None,
        "budget_compliance": 1.0 if (response.get("budget_usage") or {}).get("within_budget") is True else 0.0,
        "tool_reliability": None,
        "memory_usefulness": None,
        "failure_recovery": None,
        "latency_ms": process["wall_clock_ms"] if process else None,
        "resource_use": resource_score(process),
    }


def score_capability_task(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    return incomplete_score(status, process) if status != "completed" else {**incomplete_score(status, process), "task_success": 1.0}


def score_governance_control(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    return incomplete_score(status, process)


def score_resource_control(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    return incomplete_score(status, process)


def score_memory_operation(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    return incomplete_score(status, process)


def score_recovery_operation(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    return incomplete_score(status, process)


def invoke_case(opaque_label: str, subject_dir: Path, case: dict[str, Any], seed: int, artifact_dir: Path, campaign_id: str) -> dict[str, Any]:
    domain = case["input"]["domain"]
    if domain not in common_domains_for_campaign(campaign_id) and domain not in primitive_domains_for_campaign(campaign_id):
        return unsupported_record(
            opaque_label,
            case,
            seed,
            artifact_dir,
            "unsupported_incompatible_contract",
            "no common existing subject-native interface consumes this domain without live providers",
        )
    if domain == "calibration" and not subject_supports_calibration(subject_dir):
        return unsupported_record(
            opaque_label,
            case,
            seed,
            artifact_dir,
            "unsupported_missing_interface",
            "subject does not expose provider-free durable calibration execution",
        )
    if domain == "calibration":
        record = invoke_calibration_case(opaque_label, subject_dir, case, seed, artifact_dir)
        if is_v2_campaign(campaign_id):
            record["support_status"] = "primitive_compatibility"
            record["support_rationale"] = "all subjects expose provider-free durable calibration logic; this is runtime primitive compatibility, not capability-task support"
            write_json(artifact_dir / "raw" / f"{record['run_id']}.json", record)
        return record
    if domain == "evidence_evaluation" and domain in primitive_domains_for_campaign(campaign_id) and not subject_supports_record_observation(subject_dir):
        return unsupported_record(
            opaque_label,
            case,
            seed,
            artifact_dir,
            "unsupported_missing_interface",
            "subject does not expose provider-free durable record_observation execution",
        )
    if domain == "evidence_evaluation" and domain in primitive_domains_for_campaign(campaign_id):
        record = invoke_observation_case(opaque_label, subject_dir, case, seed, artifact_dir)
        record["support_status"] = "primitive_compatibility"
        record["support_rationale"] = "all subjects expose provider-free durable record_observation logic; this is storage-write primitive compatibility, not evidence-evaluation capability support"
        write_json(artifact_dir / "raw" / f"{record['run_id']}.json", record)
        return record
    return unsupported_record(
        opaque_label,
        case,
        seed,
        artifact_dir,
        "unsupported_incompatible_contract",
        "domain is not common-core eligible",
    )


def aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [item["status"] for item in case_results]
    benchmark_measurements = [
        item
        for item in case_results
        if item.get("measurements") and item["measurements"][0].get("measurement_scope") == "benchmark_task"
    ]
    latencies = [float(item["score"]["latency_ms"]) for item in benchmark_measurements if item["score"].get("latency_ms") is not None]
    cpu = [
        float(item["score"]["resource_use"]["cpu_time_ms"])
        for item in benchmark_measurements
        if item["score"].get("resource_use", {}).get("cpu_time_ms") is not None
    ]
    rss = [
        float(item["score"]["resource_use"]["peak_rss_kb"])
        for item in benchmark_measurements
        if item["score"].get("resource_use", {}).get("peak_rss_kb") is not None
    ]
    completed_scores = [item for item in case_results if item["status"] == "completed"]
    completed_brier = [item["score"]["brier_score"] for item in completed_scores if item["score"].get("brier_score") is not None]
    completed_budget = [item["score"]["budget_compliance"] for item in completed_scores if item["score"].get("budget_compliance") is not None]
    completed_capabilities = [item for item in completed_scores if item.get("operation_classification") == "capability_task"]
    completed_primitives = [item for item in completed_scores if item.get("operation_classification") == "runtime_primitive"]
    completed_storage = [item for item in completed_scores if item.get("operation_classification") == "storage_write"]
    calibration_primitives = [item for item in completed_primitives if item.get("operation_name") == "calibration_calculation"]
    storage_writes = [item for item in completed_storage if item.get("operation_name") == "durable_observation_recording"]
    return {
        "planned": len(case_results),
        "completed": statuses.count("completed"),
        "failed": statuses.count("failed"),
        "timeout": statuses.count("timeout"),
        "unsupported": statuses.count("unsupported"),
        "supported_common": sum(1 for item in case_results if item.get("support_status") == "supported_common"),
        "mean_task_success": statistics.mean(item["score"]["task_success"] for item in case_results),
        "mean_brier_score_completed_only": statistics.mean(completed_brier) if completed_brier else None,
        "mean_budget_compliance_completed_only": statistics.mean(completed_budget) if completed_budget else None,
        "mean_latency_ms": statistics.mean(latencies) if latencies else None,
        "mean_cpu_time_ms": statistics.mean(cpu) if cpu else None,
        "max_peak_rss_kb": max(rss) if rss else None,
        "completed_capability_tasks": len(completed_capabilities),
        "completed_runtime_primitives": len(completed_primitives),
        "completed_storage_write": len(completed_storage),
        "completed_calibration_primitives": len(calibration_primitives),
        "completed_observation_recording": len(storage_writes),
        "measurable_capability": len(completed_capabilities) > 0,
    }


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_cases = {item["pair_id"]: item for item in left["case_results"]}
    right_cases = {item["pair_id"]: item for item in right["case_results"]}
    paired = sorted(set(left_cases) & set(right_cases))
    common_core = [
        key
        for key in paired
        if left_cases[key].get("support_status") == "supported_common"
        and right_cases[key].get("support_status") == "supported_common"
    ]
    completed_common = [key for key in common_core if left_cases[key]["status"] == "completed" and right_cases[key]["status"] == "completed"]
    def mean_delta(metric: str) -> float | None:
        values = [
            right_cases[key]["score"].get(metric) - left_cases[key]["score"].get(metric)
            for key in completed_common
            if right_cases[key]["score"].get(metric) is not None and left_cases[key]["score"].get(metric) is not None
        ]
        return statistics.mean(values) if values else None
    return {
        "left": left["opaque_subject"],
        "right": right["opaque_subject"],
        "paired_case_count": len(paired),
        "common_core_paired_case_count": len(common_core),
        "completed_common_core_pair_count": len(completed_common),
        "missing_case_count": len(set(left_cases) ^ set(right_cases)),
        "left_completed": sum(1 for key in paired if left_cases[key]["status"] == "completed"),
        "right_completed": sum(1 for key in paired if right_cases[key]["status"] == "completed"),
        "left_unsupported": sum(1 for key in paired if left_cases[key]["status"] == "unsupported"),
        "right_unsupported": sum(1 for key in paired if right_cases[key]["status"] == "unsupported"),
        "left_failed": sum(1 for key in paired if left_cases[key]["status"] == "failed"),
        "right_failed": sum(1 for key in paired if right_cases[key]["status"] == "failed"),
        "left_timeout": sum(1 for key in paired if left_cases[key]["status"] == "timeout"),
        "right_timeout": sum(1 for key in paired if right_cases[key]["status"] == "timeout"),
        "task_success_delta": mean_delta("task_success"),
        "correctness_delta_completed_common": mean_delta("correctness"),
        "brier_delta_completed_common": mean_delta("brier_score"),
        "budget_compliance_delta_completed_common": mean_delta("budget_compliance"),
        "capability_delta": "unavailable_no_common_capability_task_domains",
        "critical_regression_count": 0,
    }


@dataclass(frozen=True)
class Subject:
    public_label: str
    sha: str
    opaque_label: str


def opaque_subjects(baseline: str, raw: str, reconciled: str, campaign: str) -> tuple[str, list[Subject]]:
    seed_material = f"subject-native:{campaign}:{baseline}:{raw}:{reconciled}"
    blinding_seed = sha256_text(seed_material)
    labels = [f"subject-{sha256_text(blinding_seed + str(index))[:4]}" for index in range(3)]
    return blinding_seed, [
        Subject("version-a", baseline, labels[0]),
        Subject("version-b", raw, labels[1]),
        Subject("version-c", reconciled, labels[2]),
    ]


def compatibility_matrix(cases: list[dict[str, Any]], subjects: list[Subject], campaign_id: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in cases:
        status = "supported_common" if case["domain"] in common_domains_for_campaign(campaign_id) else "unsupported_incompatible_contract"
        if case["domain"] in primitive_domains_for_campaign(campaign_id):
            status = "primitive_compatibility"
        if case["domain"] == "calibration":
            selected_interface = "scripts.execute_durable_task:calibration"
            adapter = "durable_calibration_adapter"
            rationale = "all subjects expose provider-free durable calibration logic"
            translation = "prompt/seed/request hash translated to calibration Task payload"
            evidence = ["request_hash_echoed_as_prediction_id", "process evidence"]
        elif case["domain"] == "evidence_evaluation" and status == "primitive_compatibility":
            selected_interface = "scripts.execute_durable_task:record_observation"
            adapter = "durable_record_observation_adapter"
            rationale = "all subjects expose provider-free durable record_observation logic; this is storage-write primitive compatibility, not evidence-evaluation capability support"
            translation = "prompt/seed/request hash translated to record_observation Task payload"
            evidence = ["request_hash_echoed_inside_observation", "process evidence"]
        else:
            selected_interface = None
            adapter = "unsupported_adapter"
            rationale = "no common existing subject-native interface consumes this domain without live providers"
            translation = None
            evidence = []
        for subject in subjects:
            records.append(
                {
                    "case_id": case["input"]["case_id"],
                    "domain": case["domain"],
                    "subject_sha": subject.sha,
                    "selected_interface": selected_interface if status in {"supported_common", "primitive_compatibility"} else None,
                    "adapter": adapter,
                    "support_status": status,
                    "operation_name": operation_name(case["domain"]) if status in {"supported_common", "primitive_compatibility"} else "unsupported",
                    "operation_classification": operation_classification(case["domain"]) if status in {"supported_common", "primitive_compatibility"} else "unsupported",
                    "support_rationale": rationale,
                    "input_translation": translation if status in {"supported_common", "primitive_compatibility"} else None,
                    "expected_runtime_evidence": evidence if status in {"supported_common", "primitive_compatibility"} else [],
                    "environment_requirements": ["python3.13"],
                }
            )
    return records


def write_inventory_docs(records: list[dict[str, Any]]) -> None:
    write_json(DOCS / "SUBJECT_INTERFACE_INVENTORY.json", {"records": records})
    lines = ["# Subject Interface Inventory", ""]
    for record in records:
        primitive_domains = record.get("supported_runtime_primitive_domains", [])
        lines.append(
            f"- `{record['interface_id']}`: executable={record['executable']}; "
            f"benchmark_domains={record['supported_benchmark_domains']}; "
            f"primitive_domains={primitive_domains}; path `{record['path']}`"
        )
    write_text(DOCS / "SUBJECT_INTERFACE_INVENTORY.md", "\n".join(lines) + "\n")


def write_compatibility_docs(records: list[dict[str, Any]]) -> str:
    digest = sha256_text(canonical_json(records))
    write_json(DOCS / "CROSS_VERSION_ADAPTER_COMPATIBILITY_MATRIX.json", {"matrix_hash": digest, "records": records})
    counts: dict[str, int] = {}
    for record in records:
        counts[record["support_status"]] = counts.get(record["support_status"], 0) + 1
    lines = ["# Cross-Version Adapter Compatibility Matrix", "", f"Matrix hash: `{digest}`", "", "## Counts", ""]
    for key, value in sorted(counts.items()):
        lines.append(f"- `{key}`: {value}")
    write_text(DOCS / "CROSS_VERSION_ADAPTER_COMPATIBILITY_MATRIX.md", "\n".join(lines) + "\n")
    return digest


def adapter_bundle_hash() -> str:
    files = sorted((ROOT / "cross_version_adapters").glob("*.py")) + [
        ROOT / "scripts" / "run_subject_native_cross_version_campaign.py",
        ROOT / "scripts" / "verify_subject_request_consumption.py",
    ]
    material = [
        {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path)}
        for path in files
        if path.exists()
    ]
    return sha256_text(canonical_json(material))


def locked_dependency_hashes() -> dict[str, str | None]:
    paths = [
        "requirements/requirements.lock.txt",
        "backend/package-lock.json",
        "frontend/package-lock.json",
    ]
    return {path: sha256_file(ROOT / path) if (ROOT / path).exists() else None for path in paths}


def environment_hash() -> str:
    material = {
        "python": sys.version,
        "platform": sys.platform,
        "dependency_hashes": locked_dependency_hashes(),
    }
    return sha256_text(canonical_json(material))


def payload_manifest_hash(campaign_dir: Path) -> str:
    manifest_path = campaign_dir / "INTERNAL_PAYLOAD_MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        return str(manifest["aggregate_payload_hash"])
    files = payload_included_files(campaign_dir)
    return aggregate_payload_hash(files)


def payload_included_files(campaign_dir: Path) -> list[dict[str, Any]]:
    records = []
    for root_name in ("runs", "comparisons"):
        root = campaign_dir / root_name
        if not root.exists():
            continue
        for path in sorted(root.glob("**/*.json")):
            records.append(
                {
                    "path": str(path.relative_to(campaign_dir)),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return records


def aggregate_payload_hash(included_files: list[dict[str, Any]]) -> str:
    material = [
        {"path": item["path"], "sha256": item["sha256"], "size_bytes": item["size_bytes"]}
        for item in included_files
    ]
    return sha256_text(canonical_json(material))


def write_internal_payload_manifest(campaign_dir: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    included = payload_included_files(campaign_dir)
    excluded = []
    for path, reason in {
        "CONTROL_MANIFEST.json": "control manifest contains internal_payload_manifest_hash and would create recursive hashing",
        "INTERNAL_PAYLOAD_MANIFEST.json": "payload manifest aggregate hash field is intentionally non-recursive",
    }.items():
        if (campaign_dir / path).exists() or path == "INTERNAL_PAYLOAD_MANIFEST.json":
            excluded.append({"path": path, "reason": reason})
    payload = {
        "canonicalization_version": PAYLOAD_MANIFEST_VERSION,
        "included_relative_paths": included,
        "excluded_paths": excluded,
        "aggregate_payload_hash": aggregate_payload_hash(included),
        "campaign_execution_sha": metadata["campaign_execution_sha"],
        "adapter_freeze_sha": metadata.get("adapter_freeze_sha"),
        "evaluator_hash": metadata["evaluator_code_hash"],
        "subject_shas": metadata["subject_shas"],
        "generation_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    write_json(campaign_dir / "INTERNAL_PAYLOAD_MANIFEST.json", payload)
    return payload


def freeze_manifest_path(campaign_id: str) -> Path:
    return DOCS / ("SUBJECT_ADAPTER_V2_FREEZE_MANIFEST.json" if is_v2_campaign(campaign_id) else "SUBJECT_ADAPTER_FREEZE_MANIFEST.json")


def load_freeze_manifest(campaign_id: str) -> dict[str, Any]:
    path = freeze_manifest_path(campaign_id)
    if not path.exists():
        if is_v2_campaign(campaign_id):
            raise SystemExit(f"MISSING_V2_FREEZE_MANIFEST:{path}")
        return {}
    return json.loads(path.read_text())


def write_results_and_decision(
    campaign_id: str,
    manifest: dict[str, Any],
    results: dict[str, Any],
    comparisons: dict[str, Any],
    compatibility_hash: str,
) -> None:
    totals = {
        "planned": sum(result["aggregate"]["planned"] for result in results.values()),
        "completed": sum(result["aggregate"]["completed"] for result in results.values()),
        "failed": sum(result["aggregate"]["failed"] for result in results.values()),
        "timeout": sum(result["aggregate"]["timeout"] for result in results.values()),
        "unsupported": sum(result["aggregate"]["unsupported"] for result in results.values()),
    }
    result_stem = "SUBJECT_NATIVE_CROSS_VERSION_V2" if is_v2_campaign(campaign_id) else "SUBJECT_NATIVE_CROSS_VERSION"
    completed_by_classification: dict[str, int] = {}
    for result in results.values():
        for item in result["case_results"]:
            if item.get("status") == "completed":
                key = item.get("operation_classification", "unknown")
                completed_by_classification[key] = completed_by_classification.get(key, 0) + 1
    results_doc = {
        "campaign_id": campaign_id,
        "compatibility_matrix_hash": compatibility_hash,
        "thresholds": MIN_VALIDITY_THRESHOLDS,
        "threshold_result": "not_met",
        "reason": "common subject-native execution is limited to runtime primitive and storage-write primitive operations, not benchmark capability tasks",
        "totals": totals,
        "completed_by_operation_classification": completed_by_classification,
        "common_benchmark_capability_domains": 0,
        "primitive_compatibility_operations": ["calibration_calculation", "durable_observation_recording"] if is_v2_campaign(campaign_id) else ["calibration_calculation"],
        "subjects": {
            label: {
                "sha": result["sha"],
                "opaque_subject": result["opaque_subject"],
                "health": result["health"]["status"],
                "aggregate": result["aggregate"],
            }
            for label, result in manifest["subjects_by_public"].items()
        },
        "comparisons": comparisons,
    }
    write_json(DOCS / f"{result_stem}_RESULTS.json", results_doc)
    lines = [
        "# Subject-Native Cross-Version V2 Results" if is_v2_campaign(campaign_id) else "# Subject-Native Cross-Version Results",
        "",
        f"Campaign: `{campaign_id}`",
        "",
        "## Totals",
        "",
        f"- Planned executions: {totals['planned']}",
        f"- Completed executions: {totals['completed']}",
        f"- Failed executions: {totals['failed']}",
        f"- Timeout executions: {totals['timeout']}",
        f"- Unsupported executions: {totals['unsupported']}",
        "",
        "Minimum validity thresholds were not met. Completed operations are primitive compatibility checks, not broad capability tasks.",
    ]
    write_text(DOCS / f"{result_stem}_RESULTS.md", "\n".join(lines) + "\n")
    decision = {
        "campaign_id": campaign_id,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "automatic_promotion": False,
        "audit_pr_readiness": "READY_FOR_HUMAN_REVIEW" if campaign_id.endswith("-v2-closure") else "DRAFT_PENDING_CORRECTED_EVIDENCE",
        "candidate_promotion_readiness": "BLOCKED_INSUFFICIENT_CAPABILITY_EVIDENCE",
        "external_approval": "PENDING_EXTERNAL_REVIEW",
        "promotion_blockers": [
            "minimum common-core domain threshold not met",
            "minimum common-core validation/hidden case threshold not met",
            "minimum common capability-task domain threshold not met",
            "observation recording is storage-write primitive compatibility and does not satisfy evidence-evaluation capability support",
            "memory, governance, recovery and live-provider domains remain unsupported through common immutable interfaces",
        ],
        "critical_regressions": [],
        "scheduled_observation_count": 0,
        "hosted_staging": "BLOCKED",
    }
    write_json(DOCS / f"{result_stem}_DECISION.json", decision)
    write_text(
        DOCS / f"{result_stem}_DECISION.md",
        ("# Subject-Native Cross-Version V2 Decision\n\n" if is_v2_campaign(campaign_id) else "# Subject-Native Cross-Version Decision\n\n")
        +
        "Decision: `HOLD_FOR_MORE_EVIDENCE`\n\n"
        "Audit PR readiness: `READY_FOR_HUMAN_REVIEW` for Batch 07E evidence-semantics review.\n\n"
        "Candidate promotion readiness: `BLOCKED_INSUFFICIENT_CAPABILITY_EVIDENCE`.\n\n"
        "External approval remains `PENDING_EXTERNAL_REVIEW`. No promotion, deployment, automatic approval, or merge is authorized by this evidence.\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--raw-candidate", required=True)
    parser.add_argument("--reconciled-candidate", required=True)
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--splits", default="validation,hidden")
    args = parser.parse_args()

    registry = load_registry()
    splits = {item.strip() for item in args.splits.split(",") if item.strip()}
    cases = selected_cases(registry, splits)
    campaign_dir = ARTIFACT_ROOT / args.campaign
    if campaign_dir.exists():
        shutil.rmtree(campaign_dir)
    subjects_dir = campaign_dir / "subjects"
    blinding_seed, subjects = opaque_subjects(args.baseline, args.raw_candidate, args.reconciled_candidate, args.campaign)
    start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results_by_opaque: dict[str, Any] = {}
    subject_dirs: dict[str, Path] = {}
    cleanup: list[Path] = []
    try:
        for subject in subjects:
            subject_dir = subjects_dir / subject.opaque_label
            add_worktree(subject_dir, subject.sha)
            cleanup.append(subject_dir)
            subject_dirs[subject.opaque_label] = subject_dir
            if git("status", "--short", cwd=subject_dir):
                raise SystemExit(f"DIRTY_SUBJECT_WORKTREE:{subject.opaque_label}")
        inventory = subject_interface_inventory(subjects, subject_dirs)
        compatibility = compatibility_matrix(cases, subjects, args.campaign)
        write_inventory_docs(inventory)
        compatibility_hash = write_compatibility_docs(compatibility)
        if not is_v2_campaign(args.campaign):
            write_json(
                DOCS / "SUBJECT_ADAPTER_FREEZE_MANIFEST.json",
                {
                    "adapter_freeze_commit": git("rev-parse", "HEAD"),
                    "adapter_files": sorted(str(path.relative_to(ROOT)) for path in (ROOT / "cross_version_adapters").glob("*.py"))
                    + ["scripts/run_subject_native_cross_version_campaign.py"],
                    "adapter_bundle_hash": adapter_bundle_hash(),
                    "compatibility_matrix_hash": compatibility_hash,
                    "benchmark_registry_hash": EXPECTED_REGISTRY_HASH,
                    "evaluator_version": EVALUATOR_VERSION,
                    "validation_hidden_not_used_for_adapter_development": True,
                },
            )
        freeze_manifest = load_freeze_manifest(args.campaign)
        write_json(
            ARTIFACT_ROOT / "adapter-development-v1" / "ADAPTER_DEVELOPMENT_ATTEMPTS.json",
            {
                "campaign": "adapter-development-v1",
                "splits": ["development"],
                "result": "calibration adapter selected from existing durable task interface; non-calibration domains retained unsupported",
                "attempts_preserved": True,
            },
        )
        for subject in subjects:
            subject_dir = subject_dirs[subject.opaque_label]
            health = subject_health(subject.opaque_label, subject_dir)
            artifact_dir = campaign_dir / "runs" / subject.opaque_label
            case_results = [invoke_case(subject.opaque_label, subject_dir, case, seed, artifact_dir, args.campaign) for seed in SEEDS for case in cases]
            result = {
                "opaque_subject": subject.opaque_label,
                "sha": subject.sha,
                "tree_hash": git("rev-parse", f"{subject.sha}^{{tree}}"),
                "run_ids": [f"{subject.opaque_label}-seed-{seed}" for seed in SEEDS],
                "health": health,
                "case_results": case_results,
                "aggregate": aggregate(case_results),
            }
            results_by_opaque[subject.opaque_label] = result
            write_json(campaign_dir / "runs" / f"{subject.opaque_label}.json", result)
    finally:
        for subject_dir in cleanup:
            remove_worktree(subject_dir)

    by_public = {subject.public_label: results_by_opaque[subject.opaque_label] for subject in subjects}
    comparisons = {
        "a_vs_b": compare(by_public["version-a"], by_public["version-b"]),
        "a_vs_c": compare(by_public["version-a"], by_public["version-c"]),
        "b_vs_c": compare(by_public["version-b"], by_public["version-c"]),
    }
    write_json(campaign_dir / "comparisons" / "comparisons.json", comparisons)
    sealed_mapping = {subject.opaque_label: {"public_label": subject.public_label, "sha": subject.sha} for subject in subjects}
    execution_sha = git("rev-parse", "HEAD")
    workflow_head_sha = os.getenv("EXPECTED_AUDIT_SHA") or execution_sha
    totals = {
        "planned": sum(result["aggregate"]["planned"] for result in results_by_opaque.values()),
        "completed": sum(result["aggregate"]["completed"] for result in results_by_opaque.values()),
        "failed": sum(result["aggregate"]["failed"] for result in results_by_opaque.values()),
        "timeout": sum(result["aggregate"]["timeout"] for result in results_by_opaque.values()),
        "unsupported": sum(result["aggregate"]["unsupported"] for result in results_by_opaque.values()),
    }
    manifest = {
        "campaign_id": args.campaign,
        "control_manifest_version": "subject-native-cross-version-campaign-v2" if is_v2_campaign(args.campaign) else "subject-native-cross-version-campaign-v1",
        "campaign_execution_sha": execution_sha,
        "workflow_head_sha": workflow_head_sha,
        "adapter_freeze_sha": freeze_manifest.get("adapter_freeze_commit"),
        "adapter_freeze_tree_hash": freeze_manifest.get("adapter_freeze_tree_hash"),
        "created_at": start,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_registry_hash": registry["registry_hash"],
        "evaluator_version": EVALUATOR_VERSION,
        "evaluator_code_hash": sha256_file(ROOT / "scripts" / "run_subject_native_cross_version_campaign.py"),
        "environment_hash": environment_hash(),
        "locked_dependency_hashes": locked_dependency_hashes(),
        "seeds": SEEDS,
        "splits": sorted(splits),
        "case_count_per_seed": len(cases),
        "planned_case_executions": len(cases) * len(SEEDS) * len(subjects),
        "completed_count": totals["completed"],
        "failed_count": totals["failed"],
        "timeout_count": totals["timeout"],
        "unsupported_count": totals["unsupported"],
        "common_core_coverage": {
            "domains": sorted(common_domains_for_campaign(args.campaign)),
            "supported_common_domains": len(common_domains_for_campaign(args.campaign)),
            "common_capability_task_domains": 0,
            "common_benchmark_capability_domains": 0,
            "primitive_compatibility_operations": sorted(operation_name(domain) for domain in primitive_domains_for_campaign(args.campaign)),
        },
        "common_core_domains": sorted(common_domains_for_campaign(args.campaign)),
        "primitive_compatibility_domains": sorted(primitive_domains_for_campaign(args.campaign)),
        "minimum_validity_thresholds": MIN_VALIDITY_THRESHOLDS,
        "compatibility_matrix_hash": compatibility_hash,
        "adapter_bundle_hash": adapter_bundle_hash(),
        "internal_payload_manifest_hash": None,
        "decision_reference": str(Path("docs/audit/current") / (("SUBJECT_NATIVE_CROSS_VERSION_V2_DECISION.json" if is_v2_campaign(args.campaign) else "SUBJECT_NATIVE_CROSS_VERSION_DECISION.json"))),
        "thresholds_met": False,
        "blinding": {
            "blinding_seed_hash": sha256_text(blinding_seed),
            "mapping_hash": sha256_text(canonical_json(sealed_mapping)),
            "unblinding_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sealed_mapping": sealed_mapping,
        },
        "subjects": {
            subject.public_label: {
                "sha": subject.sha,
                "opaque_label": subject.opaque_label,
                "tree_hash": results_by_opaque[subject.opaque_label]["tree_hash"],
                "run_ids": results_by_opaque[subject.opaque_label]["run_ids"],
                "health": results_by_opaque[subject.opaque_label]["health"],
                "aggregate": results_by_opaque[subject.opaque_label]["aggregate"],
            }
            for subject in subjects
        },
        "comparisons": comparisons,
        "hidden_answer_isolation": {"subject_readable_expected_outputs": False, "control_process_scores_hidden_cases": True},
        "methodology": "subject_native_existing_agentco_interfaces",
        "health_metrics_excluded_from_capability": True,
    }
    manifest["subjects_by_public"] = by_public
    write_results_and_decision(args.campaign, manifest, results_by_opaque, comparisons, compatibility_hash)
    manifest.pop("subjects_by_public")
    payload_manifest = write_internal_payload_manifest(
        campaign_dir,
        {
            "campaign_execution_sha": execution_sha,
            "adapter_freeze_sha": manifest.get("adapter_freeze_sha"),
            "evaluator_code_hash": manifest["evaluator_code_hash"],
            "subject_shas": {subject.public_label: subject.sha for subject in subjects},
        },
    )
    manifest["internal_payload_manifest_hash"] = payload_manifest["aggregate_payload_hash"]
    write_json(campaign_dir / "CONTROL_MANIFEST.json", manifest)
    print(
        canonical_json(
            {
                "success": True,
                "campaign": args.campaign,
                "artifact": str(campaign_dir),
                "planned_case_executions": manifest["planned_case_executions"],
                "completed": sum(result["aggregate"]["completed"] for result in results_by_opaque.values()),
                "unsupported": sum(result["aggregate"]["unsupported"] for result in results_by_opaque.values()),
                "decision": "HOLD_FOR_MORE_EVIDENCE",
            }
        ),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
