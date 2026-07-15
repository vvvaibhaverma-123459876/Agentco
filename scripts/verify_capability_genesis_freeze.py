#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import canonical_json, file_hash, git, reproduce_payload_hash  # noqa: E402
from scripts.run_governed_capability_genesis import FREEZE_DOC  # noqa: E402


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT).returncode == 0


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_blob_sha(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def logical_attestation_hash(freeze: dict[str, Any]) -> str:
    stripped = dict(freeze)
    stripped.pop("freeze_attestation_content_hash", None)
    stripped.pop("freeze_attestation_logical_hash", None)
    return hashlib.sha256(canonical_json(stripped).encode()).hexdigest()


def content_attestation_hash(freeze: dict[str, Any]) -> str:
    stripped = dict(freeze)
    stripped.pop("freeze_attestation_content_hash", None)
    return hashlib.sha256(canonical_json(stripped).encode()).hexdigest()


def registered_paths(freeze: dict[str, Any]) -> set[str]:
    return {entry["path"] for entry in freeze.get("frozen_files", [])}


def files_under_git(commit: str, directory: str) -> set[str]:
    output = git("ls-tree", "-r", "--name-only", commit, directory)
    return {line.strip() for line in output.splitlines() if line.strip()}


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
        return findings
    if subprocess.run(["git", "cat-file", "-e", f"{candidate}^{{commit}}"], cwd=ROOT).returncode != 0:
        findings.append("FREEZE_CANDIDATE_NOT_FOUND")
        return findings
    if not attestation:
        findings.append("FREEZE_ATTESTATION_MISSING")
    elif subprocess.run(["git", "cat-file", "-e", f"{attestation}^{{commit}}"], cwd=ROOT).returncode != 0:
        findings.append("FREEZE_ATTESTATION_NOT_FOUND")
    if attestation and not is_ancestor(candidate, attestation):
        findings.append("FREEZE_CANDIDATE_NOT_ANCESTOR_OF_ATTESTATION")
    if attestation and not is_ancestor(attestation, head):
        findings.append("FREEZE_ATTESTATION_NOT_ANCESTOR_OF_HEAD")
    if git("show", "-s", "--format=%T", candidate) != freeze.get("freeze_candidate_tree_hash"):
        findings.append("FREEZE_CANDIDATE_TREE_HASH_MISMATCH")
    if logical_attestation_hash(freeze) != freeze.get("freeze_attestation_logical_hash"):
        findings.append("FREEZE_ATTESTATION_LOGICAL_HASH_MISMATCH")
    if content_attestation_hash(freeze) != freeze.get("freeze_attestation_content_hash"):
        findings.append("FREEZE_ATTESTATION_CONTENT_HASH_MISMATCH")

    inventory = freeze.get("frozen_files") or []
    if not inventory:
        findings.append("FROZEN_FILE_INVENTORY_EMPTY")
    for entry in inventory:
        path = entry.get("path")
        if not path:
            findings.append("FROZEN_ENTRY_PATH_MISSING")
            continue
        try:
            candidate_bytes = git_bytes(candidate, path)
        except subprocess.CalledProcessError:
            findings.append(f"FROZEN_FILE_MISSING_AT_CANDIDATE:{path}")
            continue
        if git_blob_sha(candidate, path) != entry.get("blob_sha_at_candidate"):
            findings.append(f"FROZEN_BLOB_SHA_MISMATCH:{path}")
        if sha256_bytes(candidate_bytes) != entry.get("sha256_at_candidate"):
            findings.append(f"FROZEN_SHA256_MISMATCH:{path}")
        if len(candidate_bytes) != entry.get("size_bytes_at_candidate"):
            findings.append(f"FROZEN_SIZE_MISMATCH:{path}")
        final_path = ROOT / path
        if entry.get("required_at_final_head", True) and not final_path.exists():
            findings.append(f"FROZEN_FILE_MISSING_AT_FINAL_HEAD:{path}")
            continue
        if final_path.exists() and final_path.read_bytes() != candidate_bytes:
            findings.append(f"FROZEN_FILE_CHANGED_AFTER_CANDIDATE:{path}")

    reg = registered_paths(freeze)
    for directory in freeze.get("frozen_directories", []):
        for path in files_under_git(candidate, directory):
            if path not in reg:
                findings.append(f"UNREGISTERED_FROZEN_DIRECTORY_FILE:{path}")

    if manifest_path:
        manifest = load(manifest_path)
        required = [
            "campaign_execution_sha",
            "workflow_head_sha",
            "freeze_attestation_sha",
            "freeze_attestation_content_hash",
            "freeze_attestation_logical_hash",
        ]
        for key in required:
            if key not in manifest:
                findings.append(f"CAMPAIGN_MANIFEST_FIELD_MISSING:{key}")
        if manifest.get("campaign_execution_sha") != manifest.get("workflow_head_sha"):
            findings.append("EXECUTION_SHA_WORKFLOW_HEAD_MISMATCH")
        if manifest.get("freeze_attestation_sha") != freeze.get("freeze_attestation_sha"):
            findings.append("CAMPAIGN_FREEZE_ATTESTATION_SHA_MISMATCH")
        if manifest.get("freeze_attestation_content_hash") != freeze.get("freeze_attestation_content_hash"):
            findings.append("CAMPAIGN_FREEZE_ATTESTATION_CONTENT_HASH_MISMATCH")
        if manifest.get("freeze_attestation_logical_hash") != freeze.get("freeze_attestation_logical_hash"):
            findings.append("CAMPAIGN_FREEZE_ATTESTATION_LOGICAL_HASH_MISMATCH")
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        if not payload_path.exists():
            findings.append("INTERNAL_PAYLOAD_MANIFEST_MISSING")
        else:
            payload = load(payload_path)
            if payload.get("freeze_attestation_sha") != freeze.get("freeze_attestation_sha"):
                findings.append("PAYLOAD_FREEZE_ATTESTATION_MISMATCH")
            if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
                findings.append("INTERNAL_PAYLOAD_HASH_NOT_REPRODUCIBLE")
            if manifest.get("internal_payload_manifest_hash") != payload.get("aggregate_payload_hash"):
                findings.append("CAMPAIGN_INTERNAL_PAYLOAD_HASH_MISMATCH")
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
