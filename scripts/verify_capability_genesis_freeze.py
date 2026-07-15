#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import file_hash, git, reproduce_payload_hash  # noqa: E402
from scripts.run_governed_capability_genesis import FREEZE_DOC, hash_fields  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text())


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT).returncode == 0


def verify_manifest(manifest_path: Path | None = None) -> list[str]:
    findings: list[str] = []
    if not FREEZE_DOC.exists():
        return ["FREEZE_MANIFEST_MISSING"]
    freeze = load(FREEZE_DOC)
    head = git("rev-parse", "HEAD")
    candidate = freeze.get("freeze_candidate_sha")
    attestation = freeze.get("freeze_attestation_sha")
    if not candidate:
        findings.append("FREEZE_CANDIDATE_MISSING")
    elif not is_ancestor(candidate, head):
        findings.append("FREEZE_CANDIDATE_NOT_ANCESTOR")
    if attestation != git("rev-parse", "HEAD") and attestation and not is_ancestor(attestation, head):
        findings.append("FREEZE_ATTESTATION_NOT_ANCESTOR")
    if candidate:
        tree = git("show", "-s", "--format=%T", candidate)
        if tree != freeze.get("freeze_candidate_tree_hash"):
            findings.append("FREEZE_CANDIDATE_TREE_HASH_MISMATCH")
    current = hash_fields()
    for key, value in current.items():
        if freeze.get(key) != value:
            findings.append(f"FROZEN_BUNDLE_HASH_MISMATCH:{key}")
    if freeze.get("freeze_manifest_hash") and freeze["freeze_manifest_hash"] == file_hash(FREEZE_DOC):
        findings.append("FREEZE_MANIFEST_HASH_SELF_REFERENTIAL")
    if manifest_path:
        manifest = load(manifest_path)
        for key in ["campaign_execution_sha", "workflow_head_sha", "freeze_attestation_sha", *current.keys(), "freeze_manifest_hash"]:
            if key not in manifest:
                findings.append(f"CAMPAIGN_MANIFEST_FIELD_MISSING:{key}")
        if manifest.get("campaign_execution_sha") != manifest.get("workflow_head_sha"):
            findings.append("EXECUTION_SHA_WORKFLOW_HEAD_MISMATCH")
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        if not payload_path.exists():
            findings.append("INTERNAL_PAYLOAD_MANIFEST_MISSING")
        else:
            payload = load(payload_path)
            if payload.get("freeze_attestation_sha") != freeze.get("freeze_attestation_sha"):
                findings.append("PAYLOAD_FREEZE_ATTESTATION_MISMATCH")
            if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
                findings.append("INTERNAL_PAYLOAD_HASH_NOT_REPRODUCIBLE")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--manifest")
    args = parser.parse_args()
    findings = verify_manifest(Path(args.manifest) if args.manifest else None)
    print(json.dumps({"success": not findings, "findings": findings}, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
