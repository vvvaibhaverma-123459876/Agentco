#!/usr/bin/env python3
"""Verify Batch 09A real-provider baseline readiness without live execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import canonical_json, git  # noqa: E402
from agentco_capability.real_provider_readiness import (  # noqa: E402
    GENESIS_IDENTITY,
    PROTOCOL_IDENTITY,
    dry_run_result,
    execution_evidence_example,
    genesis_case_manifest,
    provider_config_from_env,
    provider_preflight,
    real_provider_hold_result,
    stable_hash,
    threshold_specification,
    validate_provider_config,
)


DOCS = ROOT / "docs" / "capability"
CURRENT = ROOT / "docs" / "audit" / "current"
CASE_MANIFEST = ROOT / "benchmarks" / "capability_genesis_v5" / "manifests" / "frozen_case_manifest.json"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def write_json(path: Path, data: Any) -> None:
    write(path, canonical_json(data))


def markdown_table(rows: list[tuple[str, Any]]) -> str:
    lines = ["| Field | Value |", "| --- | --- |"]
    for key, value in rows:
        if isinstance(value, (dict, list)):
            value = "`" + json.dumps(value, sort_keys=True) + "`"
        else:
            value = f"`{value}`"
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def report() -> dict[str, Any]:
    source_commit = git("rev-parse", "HEAD")
    source_tree = git("rev-parse", "HEAD^{tree}")
    branch = git("branch", "--show-current")
    status = git("status", "--short")
    generated_prefixes = (
        "?? agentco_capability/real_provider_readiness.py",
        "?? benchmarks/capability_genesis_v5/manifests/",
        "?? docs/audit/current/REAL_PROVIDER_BASELINE_READINESS.json",
        "?? docs/capability/",
        "?? schemas/real_provider_",
        "?? scripts/verify_real_provider_readiness.py",
        "?? tests/test_real_provider_readiness.py",
        " M Makefile",
        "M  Makefile",
        "M Makefile",
        " M docs/audit/current/GOVERNED_CAPABILITY_RUNTIME_FINDINGS",
    )
    status_lines = [line for line in status.splitlines() if line]
    baseline_clean = not status_lines or all(line.startswith(generated_prefixes) for line in status_lines)
    config = provider_config_from_env()
    config_validation = validate_provider_config(config, resolve_dns=False)
    preflight = provider_preflight(config, resolve_dns=False)
    case_manifest = genesis_case_manifest()
    thresholds = threshold_specification()
    dry_run = dry_run_result(config)
    hold = real_provider_hold_result(config)
    evidence = execution_evidence_example()
    readiness_failures: list[str] = []
    if case_manifest["validation_errors"]:
        readiness_failures.append("case_manifest_invalid")
    if hold["execution_attempted"]:
        readiness_failures.append("real_provider_execution_was_attempted")
    if hold["decision"] != "HOLD_FOR_MORE_EVIDENCE":
        readiness_failures.append("genesis_hold_not_preserved")
    if dry_run["capability_effect"] != "none" or dry_run["real_provider_execution"] is not False:
        readiness_failures.append("dry_run_capability_boundary_invalid")
    decision = "READY" if not readiness_failures else "HOLD"
    return {
        "branch": branch,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "working_tree_clean": baseline_clean,
        "protocol_campaign_identity": PROTOCOL_IDENTITY,
        "genesis_campaign_identity": GENESIS_IDENTITY,
        "provider_configuration_result": config_validation,
        "provider_preflight_result": preflight,
        "case_manifest": case_manifest,
        "threshold_specification": thresholds,
        "dry_run_result": dry_run,
        "governed_hold_result": hold,
        "execution_evidence_example": evidence,
        "readiness_failures": readiness_failures,
        "real_provider_campaign_readiness": decision,
        "real_provider_execution": "NOT_ATTEMPTED",
        "real_capability_baseline": "NOT_ESTABLISHED",
        "hosted_staging": "UNVERIFIED",
        "production_readiness": "UNVERIFIED",
        "report_hash": stable_hash({
            "source_commit": source_commit,
            "source_tree": source_tree,
            "provider_configuration_result": config_validation,
            "provider_preflight_result": preflight,
            "case_manifest_hash": case_manifest["case_manifest_hash"],
            "threshold_specification": thresholds,
            "dry_run_hash": dry_run["semantic_hash"],
            "hold": hold,
        }),
    }


def write_reports(data: dict[str, Any]) -> None:
    write_json(CASE_MANIFEST, data["case_manifest"])
    write_json(CURRENT / "REAL_PROVIDER_BASELINE_READINESS.json", data)
    write_json(DOCS / "BATCH_09A_READINESS_REPORT.json", data)
    baseline_rows = [
        ("branch", data["branch"]),
        ("starting main SHA", data["source_commit"]),
        ("source tree", data["source_tree"]),
        ("working tree clean", data["working_tree_clean"]),
        ("Protocol V3 campaign", data["protocol_campaign_identity"]),
        ("Genesis V5 campaign", data["genesis_campaign_identity"]),
        ("provider blockers", data["provider_preflight_result"]["failure_codes"] or data["provider_preflight_result"]["provider_preflight"]),
    ]
    write(
        DOCS / "BATCH_09A_BASELINE.md",
        "# Batch 09A Baseline\n\n"
        + markdown_table(baseline_rows)
        + "\n\nReal-provider execution remains `NOT_ATTEMPTED`; no credentials are recorded in repository files.\n",
    )
    readiness_rows = [
        ("provider configuration", data["provider_configuration_result"]["status"]),
        ("provider preflight", data["provider_preflight_result"]["provider_preflight"]),
        ("case manifest hash", data["case_manifest"]["case_manifest_hash"]),
        ("threshold decision set", data["threshold_specification"]["decisions"]),
        ("dry run capability effect", data["dry_run_result"]["capability_effect"]),
        ("Genesis HOLD decision", data["governed_hold_result"]["decision"]),
        ("campaign readiness", data["real_provider_campaign_readiness"]),
        ("real provider execution", data["real_provider_execution"]),
        ("real capability baseline", data["real_capability_baseline"]),
        ("report hash", data["report_hash"]),
    ]
    write(
        DOCS / "BATCH_09A_READINESS_REPORT.md",
        "# Batch 09A Real-Provider Baseline Readiness\n\n"
        + markdown_table(readiness_rows)
        + "\n\nThis report verifies readiness contracts only. It does not run a live provider and does not establish a real capability baseline.\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify generated readiness artifacts are current")
    args = parser.parse_args()
    data = report()
    if args.check:
        existing_path = DOCS / "BATCH_09A_READINESS_REPORT.json"
        case_path = CASE_MANIFEST
        findings = []
        if not existing_path.exists():
            findings.append("missing BATCH_09A_READINESS_REPORT.json")
        else:
            existing = json.loads(existing_path.read_text())
            if existing.get("real_provider_campaign_readiness") != data["real_provider_campaign_readiness"]:
                findings.append("BATCH_09A_READINESS_REPORT.json readiness decision is stale")
            if existing.get("case_manifest", {}).get("case_manifest_hash") != data["case_manifest"]["case_manifest_hash"]:
                findings.append("BATCH_09A_READINESS_REPORT.json case manifest hash is stale")
            if existing.get("dry_run_result", {}).get("capability_effect") != "none":
                findings.append("BATCH_09A_READINESS_REPORT.json dry-run capability boundary is invalid")
            if existing.get("governed_hold_result", {}).get("execution_attempted") is not False:
                findings.append("BATCH_09A_READINESS_REPORT.json does not preserve no-execution HOLD")
        if not case_path.exists():
            findings.append("missing frozen Genesis case manifest")
        elif json.loads(case_path.read_text()).get("case_manifest_hash") != data["case_manifest"]["case_manifest_hash"]:
            findings.append("frozen Genesis case manifest hash is stale")
        print(canonical_json({"success": not findings, "findings": findings, "readiness": data["real_provider_campaign_readiness"]}))
        return 0 if not findings else 1
    write_reports(data)
    print(canonical_json({"success": True, "readiness": data["real_provider_campaign_readiness"], "report_hash": data["report_hash"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
