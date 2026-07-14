#!/usr/bin/env python3
"""Verify subject-native campaign evidence binding and digest terminology."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = ROOT / "artifacts" / "cross-version" / "subject-native-cross-version-v2"


def canonical_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def payload_manifest_hash(campaign_dir: Path) -> str:
    files = []
    for path in sorted((campaign_dir / "runs").glob("**/*.json")) + sorted((campaign_dir / "comparisons").glob("**/*.json")):
        files.append({"path": str(path.relative_to(campaign_dir)), "sha256": sha256_file(path)})
    return sha256_text(canonical_json(files))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate(campaign_dir: Path = DEFAULT_CAMPAIGN, expected_head: str | None = None) -> list[str]:
    errors: list[str] = []
    if not campaign_dir.exists():
        return []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = load_json(manifest_path)
    freeze_sha = manifest.get("adapter_freeze_sha")
    if not freeze_sha:
        errors.append("MISSING_ADAPTER_FREEZE_SHA")
    else:
        try:
            subprocess.check_call(["git", "merge-base", "--is-ancestor", freeze_sha, manifest.get("campaign_execution_sha", "")], cwd=ROOT)
        except subprocess.CalledProcessError:
            errors.append("ADAPTER_FREEZE_NOT_ANCESTOR")
    if expected_head and manifest.get("workflow_head_sha") != expected_head:
        errors.append("WORKFLOW_HEAD_SHA_MISMATCH")
    if manifest.get("workflow_head_sha") != manifest.get("campaign_execution_sha"):
        errors.append("WORKFLOW_HEAD_DIFFERS_FROM_CAMPAIGN_SHA")
    if manifest.get("campaign_execution_sha") and manifest.get("campaign_execution_sha") != git("rev-parse", "HEAD") and expected_head is None:
        errors.append("CAMPAIGN_SHA_DIFFERS_FROM_CHECKOUT")
    if freeze_sha and manifest.get("adapter_freeze_tree_hash"):
        actual_tree = git("rev-parse", f"{freeze_sha}^{{tree}}")
        if actual_tree != manifest.get("adapter_freeze_tree_hash"):
            errors.append("ADAPTER_FREEZE_TREE_MISMATCH")
    if manifest.get("internal_payload_manifest_hash") != payload_manifest_hash(campaign_dir):
        errors.append("INTERNAL_PAYLOAD_HASH_MISMATCH")
    if "github_archive_digest" in manifest and manifest.get("github_archive_digest") == manifest.get("internal_payload_manifest_hash"):
        errors.append("INTERNAL_HASH_LABELLED_AS_GITHUB_ARCHIVE_DIGEST")
    totals = {"completed": 0, "failed": 0, "timeout": 0, "unsupported": 0, "planned": 0}
    for public_label, subject in manifest.get("subjects", {}).items():
        opaque = subject.get("opaque_label")
        run_path = campaign_dir / "runs" / f"{opaque}.json"
        if not run_path.exists():
            errors.append(f"MISSING_RUN:{public_label}")
            continue
        run = load_json(run_path)
        if run.get("sha") != subject.get("sha"):
            errors.append(f"SUBJECT_SHA_MISMATCH:{public_label}")
        if run.get("tree_hash") != subject.get("tree_hash"):
            errors.append(f"SUBJECT_TREE_HASH_MISMATCH:{public_label}")
        cases = run.get("case_results", [])
        totals["planned"] += len(cases)
        for item in cases:
            status = item.get("status")
            if status in totals:
                totals[status] += 1
            raw_path = campaign_dir / "runs" / str(opaque) / "raw" / f"{item.get('run_id')}.json"
            if not raw_path.exists():
                errors.append(f"MISSING_RAW_RESULT:{public_label}:{item.get('case_id')}")
    if totals["planned"] != manifest.get("planned_case_executions"):
        errors.append("PLANNED_TOTAL_MISMATCH")
    if totals["completed"] != manifest.get("completed_count"):
        errors.append("COMPLETED_TOTAL_MISMATCH")
    if totals["failed"] != manifest.get("failed_count"):
        errors.append("FAILED_TOTAL_MISMATCH")
    if totals["timeout"] != manifest.get("timeout_count"):
        errors.append("TIMEOUT_TOTAL_MISMATCH")
    if totals["unsupported"] != manifest.get("unsupported_count"):
        errors.append("UNSUPPORTED_TOTAL_MISMATCH")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--campaign-dir", type=Path, default=DEFAULT_CAMPAIGN)
    parser.add_argument("--expected-head")
    args = parser.parse_args()
    errors = validate(args.campaign_dir, args.expected_head)
    print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
