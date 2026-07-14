#!/usr/bin/env python3
"""Validate longitudinal workflow evidence against an exact commit.

This verifier is intentionally strict about evidence classification. GitHub
workflow artifacts may prove protocol execution; they do not prove hosted
AgentCo runtime or production operation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "benchmarks" / "registry.json"
LOCKFILE = ROOT / "requirements" / "requirements.lock.txt"
ALLOWED_PROVIDERS = {
    "deterministic_fixture",
    "simulated",
    "local_model",
    "local_real_service",
    "live_external_provider",
    "hosted_staging",
    "production",
}
OBSERVATION_RE = re.compile(r"^(weekly-foundation-v1-\d{4}-W\d{2}-[0-9a-f]{12}|manual-\d{8}T\d{6}Z-[0-9a-f]{12}-\d+)$")


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(data: Any) -> str:
    return sha256_bytes(canonical_json(data).encode())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(data))


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def dirty_status() -> str:
    return "dirty" if git_value("status", "--porcelain") else "clean"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def registry_hash() -> str:
    registry = json.loads(REGISTRY.read_text())
    return registry["registry_hash"]


def context_for(args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    commit12 = args.expected_sha[:12]
    event = args.event_name
    if event == "schedule":
        iso = datetime.now(UTC).isocalendar()
        observation_id = f"{args.campaign_series}-{iso.year}-W{iso.week:02d}-{commit12}"
        observation_kind = "scheduled"
    elif event == "workflow_dispatch":
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        observation_id = f"manual-{stamp}-{commit12}-{args.github_run_id}"
        observation_kind = "manual"
    elif event == "pull_request":
        observation_id = f"protocol-pr-{commit12}-{args.github_run_id}"
        observation_kind = "pull_request_protocol"
    else:
        observation_id = f"protocol-{event}-{commit12}-{args.github_run_id}"
        observation_kind = "protocol"
    attempt_id = f"{observation_id}-attempt-{args.github_run_attempt}"
    return {
        "context_version": "longitudinal-workflow-context-v1",
        "event_name": event,
        "expected_sha": args.expected_sha,
        "actual_sha": git_value("rev-parse", "HEAD"),
        "branch": git_value("branch", "--show-current"),
        "dirty_status": dirty_status(),
        "campaign_series": args.campaign_series,
        "observation_kind": observation_kind,
        "observation_id": observation_id,
        "attempt_id": attempt_id,
        "github_run_id": args.github_run_id,
        "github_run_attempt": args.github_run_attempt,
        "repository": os.environ.get("GITHUB_REPOSITORY", "local"),
        "workflow_name": os.environ.get("GITHUB_WORKFLOW", "local"),
        "created_at": now,
        "registry_hash": registry_hash(),
        "lockfile_hash": sha256_file(LOCKFILE),
        "python_version": platform.python_version(),
        "os": platform.platform(),
        "architecture": platform.machine(),
    }


def validate_context(context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if context["expected_sha"] != context["actual_sha"]:
        errors.append("EXPECTED_SHA_MISMATCH")
    if context["dirty_status"] != "clean":
        errors.append("WORKING_TREE_DIRTY")
    if context.get("repository") not in {None, "local", "vvvaibhaverma-123459876/Agentco"}:
        errors.append("ARTIFACT_REPOSITORY_MISMATCH")
    if context.get("workflow_name") not in {None, "local", "Longitudinal Evidence"}:
        errors.append("ARTIFACT_WORKFLOW_MISMATCH")
    kind = context["observation_kind"]
    observation_id = context["observation_id"]
    if kind in {"scheduled", "manual"} and not OBSERVATION_RE.match(observation_id):
        errors.append("INVALID_OBSERVATION_ID")
    if kind == "scheduled" and observation_id.startswith("initial-foundation-v1"):
        errors.append("FIXED_CAMPAIGN_ID_REUSED_FOR_SCHEDULE")
    if kind == "manual" and not observation_id.startswith("manual-"):
        errors.append("MANUAL_OBSERVATION_NOT_MARKED_MANUAL")
    if context.get("event_name") == "pull_request" and kind in {"scheduled", "manual"}:
        errors.append("UNMERGED_WORKFLOW_CLAIMS_ACTIVE_CAMPAIGN")
    return errors


def verify_chain(run_dir: Path, run_id: str) -> list[str]:
    errors: list[str] = []
    chain_path = run_dir / "EVIDENCE_CHAIN.json"
    case_path = run_dir / "CASE_RESULTS.json"
    if not chain_path.exists() or not case_path.exists():
        return [f"{run_id}:MISSING_EVIDENCE_ARTIFACT"]
    chain = json.loads(chain_path.read_text())
    cases = json.loads(case_path.read_text())
    previous = None
    if len(chain) != len(cases):
        errors.append(f"{run_id}:EVIDENCE_CHAIN_LENGTH_MISMATCH")
    for index, (link, case) in enumerate(zip(chain, cases, strict=False), start=1):
        payload_hash = sha256_json(case)
        chain_hash = hashlib.sha256(f"{previous or ''}:{payload_hash}".encode()).hexdigest()
        if link.get("evidence_id") != f"{run_id}-evidence-{index:03d}":
            errors.append(f"{run_id}:EVIDENCE_ID_MISMATCH")
        if link.get("payload_hash") != payload_hash:
            errors.append(f"{run_id}:EVIDENCE_PAYLOAD_HASH_MISMATCH")
        if link.get("previous_hash") != previous:
            errors.append(f"{run_id}:EVIDENCE_PREVIOUS_HASH_MISMATCH")
        if link.get("chain_hash") != chain_hash:
            errors.append(f"{run_id}:EVIDENCE_CHAIN_HASH_MISMATCH")
        previous = chain_hash
    return errors


def validate_campaign(path: Path, expected_sha: str, context: dict[str, Any] | None = None) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return ["MISSING_CAMPAIGN_RESULTS"]
    data = json.loads(path.read_text())
    if data.get("registry_hash") != registry_hash():
        errors.append("BENCHMARK_REGISTRY_HASH_MISMATCH")
    if data.get("evaluator_versions") != ["longitudinal-evaluator-v1"]:
        errors.append("EVALUATOR_VERSION_MISMATCH")
    run_ids = data.get("run_ids", [])
    runs = data.get("runs", [])
    if len(runs) != 5 or len(run_ids) != 5:
        errors.append("REQUIRED_SEED_RUNS_MISSING")
    seen = set()
    failure_count = 0
    for run in runs:
        run_id = run.get("run_id")
        if run_id in seen:
            errors.append("DUPLICATE_RUN_ID")
        seen.add(run_id)
        if run_id not in run_ids:
            errors.append(f"{run_id}:RUN_ID_OMITTED_FROM_SUMMARY")
        manifest = run.get("manifest", {})
        if manifest.get("commit_sha") != expected_sha:
            errors.append(f"{run_id}:MANIFEST_COMMIT_MISMATCH")
        if manifest.get("dirty_status") != "clean":
            errors.append(f"{run_id}:MANIFEST_DIRTY_STATUS")
        if not manifest.get("configuration_hash"):
            errors.append(f"{run_id}:MISSING_CONFIGURATION_HASH")
        if manifest.get("benchmark_registry_hash") != data.get("registry_hash"):
            errors.append(f"{run_id}:RUN_REGISTRY_HASH_MISMATCH")
        if manifest.get("evaluator_versions") != data.get("evaluator_versions"):
            errors.append(f"{run_id}:RUN_EVALUATOR_VERSION_MISMATCH")
        provider = manifest.get("provider_classification")
        if provider not in ALLOWED_PROVIDERS:
            errors.append(f"{run_id}:AMBIGUOUS_PROVIDER_CLASSIFICATION")
        if provider in {"hosted_staging", "production"}:
            errors.append(f"{run_id}:HOSTED_OR_PRODUCTION_CLAIM_WITHOUT_PROOF")
        if not manifest.get("output_hashes"):
            errors.append(f"{run_id}:MISSING_OUTPUT_HASHES")
        failure_count += len(run.get("failures", []))
        if context and context.get("observation_kind") in {"scheduled", "manual"} and data.get("campaign_id") != context.get("observation_id"):
            errors.append("CAMPAIGN_SUMMARY_OBSERVATION_ID_MISMATCH")
    if data.get("failure_count") != failure_count:
        errors.append("FAILED_RUN_OR_CASE_OMITTED")
    if context and data.get("campaign_id") == "initial-foundation-v1" and context.get("observation_kind") == "scheduled":
        errors.append("FIXED_CAMPAIGN_ID_REUSED_FOR_SCHEDULE")
    return errors


def emit_protocol(args: argparse.Namespace) -> int:
    context = json.loads(args.context.read_text()) if args.context else context_for(args)
    errors = validate_context(context)
    snapshot = ROOT / "docs" / "audit" / "current" / "INITIAL_LONGITUDINAL_CAMPAIGN_RESULTS.json"
    snapshot_data = json.loads(snapshot.read_text())
    if snapshot_data.get("registry_hash") != registry_hash():
        errors.append("FOUNDATION_SNAPSHOT_REGISTRY_HASH_MISMATCH")
    if snapshot_data.get("evidence_classification") not in {"L4_repeated_same_version", "repeated_same_version"}:
        errors.append("FOUNDATION_SNAPSHOT_TIER_INVALID")
    result = {
        "artifact_type": "longitudinal-protocol-validation",
        "expected_sha": context["expected_sha"],
        "actual_sha": context["actual_sha"],
        "event_name": context["event_name"],
        "observation_id": context["observation_id"],
        "attempt_id": context["attempt_id"],
        "registry_hash": registry_hash(),
        "lockfile_hash": sha256_file(LOCKFILE),
        "errors": errors,
        "success": not errors,
        "created_at": utc_now(),
    }
    write_json(args.output, result)
    print(canonical_json(result), end="")
    return 0 if not errors else 2


def emit_campaign_verification(args: argparse.Namespace) -> int:
    context = json.loads(args.context.read_text()) if args.context else None
    errors = []
    if context:
        errors.extend(validate_context(context))
    errors.extend(validate_campaign(args.campaign_results, args.expected_sha, context))
    if args.artifact_root.exists():
        data = json.loads(args.campaign_results.read_text()) if args.campaign_results.exists() else {"runs": []}
        for run in data.get("runs", []):
            run_id = run["run_id"]
            errors.extend(verify_chain(args.artifact_root / data["campaign_id"] / run_id, run_id))
    result = {
        "artifact_type": "longitudinal-campaign-verification",
        "expected_sha": args.expected_sha,
        "campaign_results": str(args.campaign_results),
        "errors": errors,
        "success": not errors,
        "created_at": utc_now(),
    }
    write_json(args.output, result)
    print(canonical_json(result), end="")
    return 0 if not errors else 2


def emit_failure_manifest(args: argparse.Namespace) -> int:
    if args.context and args.context.exists():
        context = json.loads(args.context.read_text())
    else:
        context = context_for(args)
    manifest = {
        "artifact_type": "longitudinal-failure-manifest",
        "observation_id": context["observation_id"],
        "attempt_id": context["attempt_id"],
        "expected_commit": context["expected_sha"],
        "actual_commit": context["actual_sha"],
        "event_type": context["event_name"],
        "start_time": context.get("created_at"),
        "completion_time": utc_now(),
        "failure_stage": args.failure_stage,
        "exit_code": args.exit_code,
        "available_partial_results": {
            "context": str(args.context) if args.context else None,
            "protocol_validation": "artifacts/longitudinal/protocol-validation.json",
            "campaign_verification": "artifacts/longitudinal/campaign-verification.json",
        },
        "cleanup_status": "not_applicable_for_protocol_validation",
    }
    manifest["artifact_hash"] = sha256_json(manifest)
    write_json(args.output, manifest)
    print(canonical_json(manifest), end="")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare-context")
    prep.add_argument("--expected-sha", required=True)
    prep.add_argument("--event-name", required=True)
    prep.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    prep.add_argument("--github-run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    prep.add_argument("--campaign-series", default="weekly-foundation-v1")
    prep.add_argument("--output", type=Path, required=True)

    obs = sub.add_parser("observation-id")
    obs.add_argument("--context", type=Path, required=True)

    protocol = sub.add_parser("protocol")
    protocol.add_argument("--expected-sha", required=True)
    protocol.add_argument("--event-name", default="pull_request")
    protocol.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    protocol.add_argument("--github-run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    protocol.add_argument("--campaign-series", default="weekly-foundation-v1")
    protocol.add_argument("--context", type=Path)
    protocol.add_argument("--output", type=Path, required=True)

    campaign = sub.add_parser("campaign")
    campaign.add_argument("--expected-sha", required=True)
    campaign.add_argument("--context", type=Path)
    campaign.add_argument("--campaign-results", type=Path, required=True)
    campaign.add_argument("--artifact-root", type=Path, default=ROOT / "artifacts" / "longitudinal")
    campaign.add_argument("--output", type=Path, required=True)

    failure = sub.add_parser("failure")
    failure.add_argument("--expected-sha", required=True)
    failure.add_argument("--event-name", required=True)
    failure.add_argument("--github-run-id", default=os.environ.get("GITHUB_RUN_ID", "local"))
    failure.add_argument("--github-run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT", "1"))
    failure.add_argument("--campaign-series", default="weekly-foundation-v1")
    failure.add_argument("--context", type=Path)
    failure.add_argument("--failure-stage", required=True)
    failure.add_argument("--exit-code", type=int, required=True)
    failure.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "prepare-context":
        context = context_for(args)
        errors = validate_context(context)
        context["errors"] = errors
        context["success"] = not errors
        write_json(args.output, context)
        print(canonical_json(context), end="")
        return 0 if not errors else 2
    if args.command == "observation-id":
        print(json.loads(args.context.read_text())["observation_id"])
        return 0
    if args.command == "protocol":
        return emit_protocol(args)
    if args.command == "campaign":
        return emit_campaign_verification(args)
    if args.command == "failure":
        return emit_failure_manifest(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
