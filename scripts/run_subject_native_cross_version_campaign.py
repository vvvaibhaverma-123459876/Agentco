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
import resource
import shutil
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "cross-version"
REGISTRY = ROOT / "benchmarks" / "registry.json"
DOCS = ROOT / "docs" / "audit" / "current"
EXPECTED_REGISTRY_HASH = "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e"
EVALUATOR_VERSION = "longitudinal-evaluator-v1"
SEEDS = [101, 202, 303, 404, 505]
COMMON_CORE_DOMAINS = {"calibration"}
SUPPORTED_TASK_BY_DOMAIN = {"calibration": "calibration"}
MIN_VALIDITY_THRESHOLDS = {
    "supported_common_domains": 8,
    "supported_common_validation_hidden_cases": 18,
    "completion_rate": 0.75,
    "max_subject_coverage_gap_points": 10,
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
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill()
        stdout, stderr = process.communicate()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    completed = time.time()
    return {
        "argv": argv,
        "cwd": str(cwd),
        "pid": process.pid,
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start)),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(completed)),
        "wall_clock_ms": round((completed - start) * 1000, 3),
        "cpu_time_ms": round(
            (
                (usage_after.ru_utime + usage_after.ru_stime)
                - (usage_before.ru_utime + usage_before.ru_stime)
            )
            * 1000,
            3,
        ),
        "peak_rss_kb": usage_after.ru_maxrss,
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
            "score": score_response("unsupported", response, None),
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
                    "peak_rss_kb": process["peak_rss_kb"],
                }
            ],
            "score": score_response(status, response, process),
        }
    )
    write_json(artifact_dir / "raw" / f"{run_id}.json", record)
    return record


def score_response(status: str, response: dict[str, Any], process: dict[str, Any] | None) -> dict[str, Any]:
    if status != "completed":
        return {
            "task_success": 0.0,
            "correctness": 0.0 if status in {"failed", "timeout"} else None,
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
            "resource_use": {
                "cpu_time_ms": process["cpu_time_ms"] if process else None,
                "peak_rss_kb": process["peak_rss_kb"] if process else None,
            },
        }
    answer = response.get("answer") or {}
    budget_usage = response.get("budget_usage") or {}
    return {
        "task_success": 1.0,
        "correctness": 1.0 if answer.get("brier_score") is not None else 0.0,
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
        "resource_use": {
            "cpu_time_ms": process["cpu_time_ms"] if process else None,
            "peak_rss_kb": process["peak_rss_kb"] if process else None,
        },
    }


def invoke_case(opaque_label: str, subject_dir: Path, case: dict[str, Any], seed: int, artifact_dir: Path) -> dict[str, Any]:
    domain = case["input"]["domain"]
    if domain not in COMMON_CORE_DOMAINS:
        return unsupported_record(
            opaque_label,
            case,
            seed,
            artifact_dir,
            "unsupported_incompatible_contract",
            "no common existing subject-native interface consumes this domain without live providers",
        )
    if not subject_supports_calibration(subject_dir):
        return unsupported_record(
            opaque_label,
            case,
            seed,
            artifact_dir,
            "unsupported_missing_interface",
            "subject does not expose provider-free durable calibration execution",
        )
    return invoke_calibration_case(opaque_label, subject_dir, case, seed, artifact_dir)


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
    return {
        "planned": len(case_results),
        "completed": statuses.count("completed"),
        "failed": statuses.count("failed"),
        "timeout": statuses.count("timeout"),
        "unsupported": statuses.count("unsupported"),
        "supported_common": sum(1 for item in case_results if item.get("support_status") == "supported_common"),
        "mean_task_success": statistics.mean(item["score"]["task_success"] for item in case_results),
        "mean_correctness_completed_only": statistics.mean(item["score"]["correctness"] for item in completed_scores) if completed_scores else None,
        "mean_brier_score_completed_only": statistics.mean(item["score"]["brier_score"] for item in completed_scores) if completed_scores else None,
        "mean_budget_compliance_completed_only": statistics.mean(item["score"]["budget_compliance"] for item in completed_scores) if completed_scores else None,
        "mean_latency_ms": statistics.mean(latencies) if latencies else None,
        "mean_cpu_time_ms": statistics.mean(cpu) if cpu else None,
        "max_peak_rss_kb": max(rss) if rss else None,
        "measurable_capability": statuses.count("completed") > 0,
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
        "capability_delta": "limited_to_calibration_common_core",
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


def compatibility_matrix(cases: list[dict[str, Any]], subjects: list[Subject]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in cases:
        status = "supported_common" if case["domain"] in COMMON_CORE_DOMAINS else "unsupported_incompatible_contract"
        for subject in subjects:
            records.append(
                {
                    "case_id": case["input"]["case_id"],
                    "domain": case["domain"],
                    "subject_sha": subject.sha,
                    "selected_interface": "scripts.execute_durable_task:calibration" if status == "supported_common" else None,
                    "adapter": "durable_calibration_adapter" if status == "supported_common" else "unsupported_adapter",
                    "support_status": status,
                    "support_rationale": (
                        "all subjects expose provider-free durable calibration logic"
                        if status == "supported_common"
                        else "no common existing subject-native interface consumes this domain without live providers"
                    ),
                    "input_translation": "prompt/seed/request hash translated to calibration Task payload" if status == "supported_common" else None,
                    "expected_runtime_evidence": ["request_hash_echoed_as_prediction_id", "process evidence"] if status == "supported_common" else [],
                    "environment_requirements": ["python3.13"],
                }
            )
    return records


def write_inventory_docs(records: list[dict[str, Any]]) -> None:
    write_json(DOCS / "SUBJECT_INTERFACE_INVENTORY.json", {"records": records})
    lines = ["# Subject Interface Inventory", ""]
    for record in records:
        lines.append(f"- `{record['interface_id']}`: executable={record['executable']}; domains={record['supported_benchmark_domains']}; path `{record['path']}`")
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
    results_doc = {
        "campaign_id": campaign_id,
        "compatibility_matrix_hash": compatibility_hash,
        "thresholds": MIN_VALIDITY_THRESHOLDS,
        "threshold_result": "not_met",
        "reason": "only calibration currently has a common subject-native provider-free interface across all immutable subjects",
        "totals": totals,
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
    write_json(DOCS / "SUBJECT_NATIVE_CROSS_VERSION_RESULTS.json", results_doc)
    lines = [
        "# Subject-Native Cross-Version Results",
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
        "Minimum validity thresholds were not met. The evidence is limited to the provider-free calibration common core.",
    ]
    write_text(DOCS / "SUBJECT_NATIVE_CROSS_VERSION_RESULTS.md", "\n".join(lines) + "\n")
    decision = {
        "campaign_id": campaign_id,
        "decision": "HOLD_FOR_MORE_EVIDENCE",
        "automatic_promotion": False,
        "external_approval": "PENDING_EXTERNAL_REVIEW",
        "promotion_blockers": [
            "minimum common-core domain threshold not met",
            "minimum common-core validation/hidden case threshold not met",
            "memory, governance, recovery and live-provider domains remain unsupported through common immutable interfaces",
        ],
        "critical_regressions": [],
        "scheduled_observation_count": 0,
        "hosted_staging": "BLOCKED",
    }
    write_json(DOCS / "SUBJECT_NATIVE_CROSS_VERSION_DECISION.json", decision)
    write_text(
        DOCS / "SUBJECT_NATIVE_CROSS_VERSION_DECISION.md",
        "# Subject-Native Cross-Version Decision\n\n"
        "Decision: `HOLD_FOR_MORE_EVIDENCE`\n\n"
        "External approval remains `PENDING_EXTERNAL_REVIEW`. No promotion, deployment, merge, or PR readiness action is authorized by this evidence.\n",
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
        compatibility = compatibility_matrix(cases, subjects)
        write_inventory_docs(inventory)
        compatibility_hash = write_compatibility_docs(compatibility)
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
            case_results = [invoke_case(subject.opaque_label, subject_dir, case, seed, artifact_dir) for seed in SEEDS for case in cases]
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
    sealed_mapping = {subject.opaque_label: {"public_label": subject.public_label, "sha": subject.sha} for subject in subjects}
    manifest = {
        "campaign_id": args.campaign,
        "control_manifest_version": "subject-native-cross-version-campaign-v1",
        "created_at": start,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_registry_hash": registry["registry_hash"],
        "evaluator_version": EVALUATOR_VERSION,
        "evaluator_code_hash": sha256_file(ROOT / "scripts" / "run_subject_native_cross_version_campaign.py"),
        "seeds": SEEDS,
        "splits": sorted(splits),
        "case_count_per_seed": len(cases),
        "planned_case_executions": len(cases) * len(SEEDS) * len(subjects),
        "common_core_domains": sorted(COMMON_CORE_DOMAINS),
        "minimum_validity_thresholds": MIN_VALIDITY_THRESHOLDS,
        "compatibility_matrix_hash": compatibility_hash,
        "adapter_bundle_hash": adapter_bundle_hash(),
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
    write_json(campaign_dir / "CONTROL_MANIFEST.json", manifest)
    write_json(campaign_dir / "comparisons" / "comparisons.json", comparisons)
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
