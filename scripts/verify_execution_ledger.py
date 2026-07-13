#!/usr/bin/env python3
"""Validate exact-HEAD runtime execution evidence."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMMAND_IDS = {
    "docker-version",
    "docker-postgres-start",
    "create-database",
    "migration-static-integrity",
    "database-empty-before-migration",
    "backend-install",
    "migrate-from-zero",
    "database-after-migration",
    "migrate-idempotency-second-run",
    "release-gate-integrity",
    "release-make-targets",
    "release-status-check",
    "release-agent-protocol-matrix-check",
    "release-evaluation-calibration-report-check",
    "release-controlled-learning-report-check",
    "release-self-improvement-report-check",
    "release-score-validation",
    "pytest-governed",
    "backend-build",
    "backend-jest",
    "backend-route-auth-contract",
    "backend-audit-chain-cross-writer",
    "frontend-install",
    "frontend-typecheck",
    "frontend-build",
    "cleanup-drop-database",
    "cleanup-remove-container",
    "cleanup-remove-volume",
    "cleanup-verify-container-removed",
    "cleanup-verify-volume-removed",
}
EXPECTED_NONZERO_COMMAND_IDS = {
    "cleanup-verify-container-removed",
    "cleanup-verify-volume-removed",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    errors: list[str] = []
    if ledger.get("commit") != head:
        errors.append(f"ledger commit {ledger.get('commit')} does not match HEAD {head}")
    if ledger.get("final_verdict") != "PASS":
        errors.append(f"ledger final verdict is {ledger.get('final_verdict')}")
    if not ledger.get("cleanup", {}).get("success"):
        errors.append("ledger cleanup did not succeed")
    commands = ledger.get("commands", [])
    if not commands:
        errors.append("ledger recorded no commands")
    run_id = ledger.get("run_id")
    seen: set[str] = set()
    for item in commands:
        command_id = item.get("command_id") or item.get("name")
        if not command_id:
            errors.append("command missing command_id")
            continue
        if command_id in seen:
            errors.append(f"duplicate command id: {command_id}")
        seen.add(command_id)
        if item.get("run_id") != run_id:
            errors.append(f"command belongs to another run: {command_id}")
        if item.get("commit") != ledger.get("commit"):
            errors.append(f"command belongs to another commit: {command_id}")
        if "exit_code" not in item:
            errors.append(f"command missing exit_code: {command_id}")
        if item.get("exit_code") != 0 and command_id not in EXPECTED_NONZERO_COMMAND_IDS:
            errors.append(f"command failed: {command_id} exit={item.get('exit_code')}")
        for artifact_key in ("stdout_artifact", "stderr_artifact"):
            artifact = item.get(artifact_key)
            if not artifact or not (args.ledger.parent / artifact).exists():
                errors.append(f"missing {artifact_key} for command {command_id}")
        serialized = json.dumps(item)
        if re.search(r"postgres(?:ql)?://[^:/@\s]+:[^<][^@\s]+@", serialized):
            errors.append(f"command record contains unredacted database credential: {command_id}")
        if re.search(r"(PASSWORD|TOKEN|SECRET|API_KEY|AUTHORIZATION)=[^<\s][^\s\"]+", serialized, re.IGNORECASE):
            errors.append(f"command record contains unredacted secret assignment: {command_id}")
    missing = sorted(REQUIRED_COMMAND_IDS - seen)
    if missing:
        errors.append(f"ledger missing required command ids: {missing}")
    print(json.dumps({"success": not errors, "errors": errors}, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
