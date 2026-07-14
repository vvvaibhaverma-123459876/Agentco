#!/usr/bin/env python3
"""Fail-closed Batch 05 hosted staging command wrapper.

The wrapper records the selected phase and validates budget/prerequisites. It
does not fabricate hosted resource identifiers. Until the execution contract is
ready and provider tooling is installed, every hosted phase exits non-zero with
UNVERIFIED_EXTERNAL_DEPENDENCY.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts/hosted-staging"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_budget_check() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/verify_hosted_staging_budget.py",
            "--check-prerequisites",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("plan", "apply", "audit", "destroy"))
    args = parser.parse_args()

    commit = git_value("rev-parse", "HEAD")
    branch = git_value("branch", "--show-current")
    run_id = f"{utc_stamp()}-{commit[:8]}-{args.phase}"
    artifact_dir = ARTIFACT_ROOT / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    budget = run_budget_check()
    ledger = {
        "run_id": run_id,
        "phase": args.phase,
        "commit": commit,
        "branch": branch,
        "started_at": datetime.now(UTC).isoformat(),
        "final_verdict": "BLOCKED",
        "evidence_classification": "UNVERIFIED_EXTERNAL_DEPENDENCY",
        "budget_check_exit_code": budget.returncode,
        "budget_check_stdout": budget.stdout,
        "budget_check_stderr": budget.stderr,
        "hosted_resources_created": [],
        "cleanup_required": False,
        "reason": "Hosted staging prerequisites are not satisfied; no hosted resources were created.",
    }
    (artifact_dir / "EXECUTION_LEDGER.json").write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    (artifact_dir / "HOSTED_STAGING_SUMMARY.md").write_text(
        "# Hosted Staging Audit Summary\n\n"
        f"- Phase: `{args.phase}`\n"
        f"- Commit: `{commit}`\n"
        f"- Branch: `{branch}`\n"
        "- Verdict: `BLOCKED`\n"
        "- Evidence classification: `UNVERIFIED_EXTERNAL_DEPENDENCY`\n"
        "- Hosted resources created: `0`\n\n"
        "The command failed closed because hosted cloud/IaC/DNS/provider prerequisites are not satisfied.\n"
    )

    print(str(artifact_dir))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
