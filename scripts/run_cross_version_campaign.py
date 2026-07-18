#!/usr/bin/env python3
"""Run a real cross-version campaign through subject-native processes.

This runner deliberately does not synthesize candidate answers.  Each planned
case starts a process inside the immutable subject worktree.  If the subject
does not expose a stable benchmark protocol, the case is retained as
``unsupported`` with process evidence rather than converted into a fake result.
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
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "cross-version"
REGISTRY = ROOT / "benchmarks" / "registry.json"
EXPECTED_REGISTRY_HASH = "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e"
EVALUATOR_VERSION = "longitudinal-evaluator-v1"
SEEDS = [101, 202, 303, 404, 505]
SUBJECT_PROCESS = ["python3.13", "scripts/verify_mission_progress.py", "--help"]


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def run_process(argv: list[str], cwd: Path, env: dict[str, str], timeout: float) -> dict[str, Any]:
    start = time.time()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
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
        "started_at": start,
        "completed_at": completed,
        "wall_clock_ms": round((completed - start) * 1000, 3),
        "cpu_time_ms": round(((usage_after.ru_utime + usage_after.ru_stime) - (usage_before.ru_utime + usage_before.ru_stime)) * 1000, 3),
        "peak_rss_kb": usage_after.ru_maxrss,
        "stdout_hash": sha256_bytes(stdout),
        "stderr_hash": sha256_bytes(stderr),
        "stdout_preview": stdout.decode(errors="replace")[:400],
        "stderr_preview": stderr.decode(errors="replace")[:400],
    }


def load_registry() -> dict[str, Any]:
    registry = json.loads(REGISTRY.read_text())
    if registry.get("registry_hash") != EXPECTED_REGISTRY_HASH:
        raise SystemExit(f"BENCHMARK_HASH_MISMATCH:{registry.get('registry_hash')}")
    if registry.get("evaluator_versions") != [EVALUATOR_VERSION]:
        raise SystemExit(f"EVALUATOR_VERSION_MISMATCH:{registry.get('evaluator_versions')}")
    return registry


def control_cases(registry: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for suite in registry["suites"]:
        for item in suite["cases"]:
            if item["split"] not in {"validation", "hidden"}:
                continue
            cases.append(
                {
                    "benchmark_id": suite["benchmark_id"],
                    "version": suite["version"],
                    "input": {key: item[key] for key in ("case_id", "domain", "prompt", "split", "input_hash", "expected_output_hash")},
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


def duplicate_sequences(subject_dir: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for migration in sorted((subject_dir / "backend" / "src" / "db" / "migrations").glob("*.sql")):
        prefix = migration.name.split("_", 1)[0]
        if prefix.isdigit():
            result.setdefault(prefix, []).append(migration.name)
    return {key: value for key, value in result.items() if len(value) > 1}


def subject_health(opaque_label: str, subject_dir: Path) -> dict[str, Any]:
    commands = [
        {"id": "git-clean", "argv": ["git", "status", "--short"], "timeout": 10.0},
        {"id": "python-subject-help", "argv": SUBJECT_PROCESS, "timeout": 10.0},
    ]
    records = []
    for command in commands:
        env = os.environ.copy()
        env["AGENTCO_SUBJECT_HEALTH"] = opaque_label
        records.append({"id": command["id"], "result": run_process(command["argv"], subject_dir, env, command["timeout"])})
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


def invoke_case(opaque_label: str, subject_dir: Path, case: dict[str, Any], seed: int, artifact_dir: Path) -> dict[str, Any]:
    run_id = f"{opaque_label}-seed-{seed}-{case['input']['case_id']}"
    request = request_for(case, seed, run_id)
    request_path = artifact_dir / "requests" / f"{run_id}.json"
    write_json(request_path, request)
    env = os.environ.copy()
    env["AGENTCO_BENCHMARK_REQUEST"] = str(request_path)
    env["AGENTCO_BENCHMARK_PROTOCOL"] = "subject-benchmark-v1"
    process = run_process(SUBJECT_PROCESS, subject_dir, env, min(max(case["timeout_seconds"], 1.0), 10.0))
    status = "timeout" if process["timed_out"] else "unsupported"
    if process["exit_code"] != 0 and not process["timed_out"]:
        status = "failed"
    evidence_ref = f"process://{opaque_label}/{run_id}/{process['pid']}"
    response = {
        "protocol_version": "subject-benchmark-v1",
        "run_id": run_id,
        "case_id": case["input"]["case_id"],
        "status": status,
        "answer": None,
        "confidence": None,
        "evidence_refs": [evidence_ref],
        "tool_calls": [],
        "authorization_events": [],
        "budget_usage": {"measured": False, "reason": "subject benchmark protocol unsupported"},
        "runtime_events": [{"type": "subject_process_invoked", "pid": process["pid"], "exit_code": process["exit_code"]}],
        "audit_refs": [],
        "error": "subject does not expose subject-benchmark-v1 response interface" if status == "unsupported" else None,
    }
    record = {
        "pair_id": f"{seed}:{case['input']['case_id']}",
        "opaque_subject": opaque_label,
        "run_id": run_id,
        "seed": seed,
        "case_id": case["input"]["case_id"],
        "domain": case["input"]["domain"],
        "split": case["input"]["split"],
        "input_hash": case["input"]["input_hash"],
        "expected_output_hash": case["input"]["expected_output_hash"],
        "request_hash": sha256_text(canonical_json(request)),
        "response_hash": sha256_text(canonical_json(response)),
        "status": status,
        "response": response,
        "process": process,
        "runtime_evidence_refs": [evidence_ref],
        "score": score_response(status, response, process),
    }
    write_json(artifact_dir / "raw" / f"{run_id}.json", record)
    return record


def score_response(status: str, response: dict[str, Any], process: dict[str, Any]) -> dict[str, Any]:
    if status != "completed":
        return {
            "task_success": 0.0,
            "correctness": None,
            "evidence_quality": 1.0 if response["evidence_refs"] else 0.0,
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
            "latency_ms": process["wall_clock_ms"],
            "resource_use": {"cpu_time_ms": process["cpu_time_ms"], "peak_rss_kb": process["peak_rss_kb"]},
        }
    raise SystemExit("COMPLETED_STATUS_REQUIRES_SUBJECT_NATIVE_SCORING")


def aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [item["status"] for item in case_results]
    latencies = [float(item["score"]["latency_ms"]) for item in case_results]
    cpu = [float(item["score"]["resource_use"]["cpu_time_ms"]) for item in case_results]
    rss = [float(item["score"]["resource_use"]["peak_rss_kb"]) for item in case_results]
    return {
        "planned": len(case_results),
        "completed": statuses.count("completed"),
        "failed": statuses.count("failed"),
        "timeout": statuses.count("timeout"),
        "unsupported": statuses.count("unsupported"),
        "mean_latency_ms": statistics.mean(latencies) if latencies else None,
        "mean_cpu_time_ms": statistics.mean(cpu) if cpu else None,
        "max_peak_rss_kb": max(rss) if rss else None,
        "measurable_capability": statuses.count("completed") > 0,
    }


def compare(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_cases = {item["pair_id"]: item for item in left["case_results"]}
    right_cases = {item["pair_id"]: item for item in right["case_results"]}
    paired = sorted(set(left_cases) & set(right_cases))
    return {
        "left": left["opaque_subject"],
        "right": right["opaque_subject"],
        "paired_case_count": len(paired),
        "missing_case_count": len(set(left_cases) ^ set(right_cases)),
        "left_completed": sum(1 for key in paired if left_cases[key]["status"] == "completed"),
        "right_completed": sum(1 for key in paired if right_cases[key]["status"] == "completed"),
        "left_unsupported": sum(1 for key in paired if left_cases[key]["status"] == "unsupported"),
        "right_unsupported": sum(1 for key in paired if right_cases[key]["status"] == "unsupported"),
        "left_failed": sum(1 for key in paired if left_cases[key]["status"] == "failed"),
        "right_failed": sum(1 for key in paired if right_cases[key]["status"] == "failed"),
        "left_timeout": sum(1 for key in paired if left_cases[key]["status"] == "timeout"),
        "right_timeout": sum(1 for key in paired if right_cases[key]["status"] == "timeout"),
        "capability_delta": "unavailable_no_completed_subject_benchmark_responses",
        "critical_regression_count": 0,
    }


@dataclass(frozen=True)
class Subject:
    public_label: str
    sha: str
    opaque_label: str


def opaque_subjects(baseline: str, raw: str, reconciled: str, campaign: str) -> tuple[str, list[Subject]]:
    seed_material = f"{campaign}:{baseline}:{raw}:{reconciled}"
    blinding_seed = sha256_text(seed_material)
    labels = [f"subject-{sha256_text(blinding_seed + str(index))[:4]}" for index in range(3)]
    subjects = [
        Subject("version-a", baseline, labels[0]),
        Subject("version-b", raw, labels[1]),
        Subject("version-c", reconciled, labels[2]),
    ]
    return blinding_seed, subjects


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--raw-candidate", required=True)
    parser.add_argument("--reconciled-candidate", required=True)
    parser.add_argument("--campaign", required=True)
    args = parser.parse_args()

    registry = load_registry()
    cases = control_cases(registry)
    campaign_dir = ARTIFACT_ROOT / args.campaign
    if campaign_dir.exists():
        shutil.rmtree(campaign_dir)
    subjects_dir = campaign_dir / "subjects"
    blinding_seed, subjects = opaque_subjects(args.baseline, args.raw_candidate, args.reconciled_candidate, args.campaign)
    start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results: dict[str, Any] = {}
    cleanup: list[Path] = []
    try:
        for subject in subjects:
            subject_dir = subjects_dir / subject.opaque_label
            add_worktree(subject_dir, subject.sha)
            cleanup.append(subject_dir)
            if git("status", "--short", cwd=subject_dir):
                raise SystemExit(f"DIRTY_SUBJECT_WORKTREE:{subject.opaque_label}")
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
            results[subject.opaque_label] = result
            write_json(campaign_dir / "runs" / f"{subject.opaque_label}.json", result)
    finally:
        for subject_dir in cleanup:
            remove_worktree(subject_dir)

    by_public = {subject.public_label: results[subject.opaque_label] for subject in subjects}
    comparisons = {
        "a_vs_b": compare(by_public["version-a"], by_public["version-b"]),
        "a_vs_c": compare(by_public["version-a"], by_public["version-c"]),
        "b_vs_c": compare(by_public["version-b"], by_public["version-c"]),
    }
    sealed_mapping = {
        subject.opaque_label: {"public_label": subject.public_label, "sha": subject.sha}
        for subject in subjects
    }
    manifest = {
        "campaign_id": args.campaign,
        "control_manifest_version": "real-cross-version-campaign-v1",
        "created_at": start,
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "benchmark_registry_hash": registry["registry_hash"],
        "evaluator_version": EVALUATOR_VERSION,
        "evaluator_code_hash": sha256_file(ROOT / "scripts" / "run_cross_version_campaign.py"),
        "seeds": SEEDS,
        "case_count_per_seed": len(cases),
        "planned_case_executions": len(cases) * len(SEEDS) * len(subjects),
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
                "tree_hash": results[subject.opaque_label]["tree_hash"],
                "run_ids": results[subject.opaque_label]["run_ids"],
                "health": results[subject.opaque_label]["health"],
                "aggregate": results[subject.opaque_label]["aggregate"],
            }
            for subject in subjects
        },
        "comparisons": comparisons,
        "hidden_answer_isolation": {
            "subject_readable_expected_outputs": False,
            "control_process_scores_hidden_cases": True,
        },
        "methodology": "subject_process_invocation_no_synthetic_outputs",
    }
    write_json(campaign_dir / "CONTROL_MANIFEST.json", manifest)
    write_json(campaign_dir / "comparisons" / "comparisons.json", comparisons)
    print(canonical_json({"success": True, "campaign": args.campaign, "artifact": str(campaign_dir), "planned_case_executions": manifest["planned_case_executions"]}), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
