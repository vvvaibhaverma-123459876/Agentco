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

from agentco_capability.evidence import canonical_json, git, reproduce_payload_hash  # noqa: E402

DOCS = ROOT / "docs" / "audit" / "current"
MANIFEST_PATH = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json"
BINDING_PATH = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json"
MANIFEST_REL = str(MANIFEST_PATH.relative_to(ROOT))
BINDING_REL = str(BINDING_PATH.relative_to(ROOT))


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def logical_hash(data: dict[str, Any], field: str) -> str:
    clean = dict(data)
    clean.pop(field, None)
    return hashlib.sha256(canonical_json(clean).encode()).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_blob(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}")


def commit_exists(commit: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT).returncode == 0


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT).returncode == 0


def changed_files(commit: str) -> list[str]:
    output = git("diff-tree", "--no-commit-id", "--name-only", "-r", commit)
    return [line for line in output.splitlines() if line.strip()]


def files_under_git(commit: str, directory: str) -> set[str]:
    output = git("ls-tree", "-r", "--name-only", commit, directory)
    return {line for line in output.splitlines() if line.strip() and "__pycache__" not in line and not line.endswith(".pyc")}


def binding_commit_from_history(head: str) -> str | None:
    output = git("log", "--format=%H", head, "--", BINDING_REL)
    commits = [line for line in output.splitlines() if line.strip()]
    return commits[0] if commits else None


def verify_manifest(manifest_path: Path | None = None) -> list[str]:
    findings: list[str] = []
    head = git("rev-parse", "HEAD")
    if not BINDING_PATH.exists():
        return ["FREEZE_BINDING_MISSING"]
    if not MANIFEST_PATH.exists():
        findings.append("FREEZE_MANIFEST_MISSING")
    binding = load(BINDING_PATH)
    binding_commit = binding_commit_from_history(head)
    if not binding_commit:
        findings.append("FREEZE_BINDING_COMMIT_NOT_FOUND")
        return findings
    candidate = binding.get("freeze_candidate_sha")
    manifest_commit = binding.get("freeze_manifest_commit_sha")
    for label, commit in {"candidate": candidate, "manifest": manifest_commit, "binding": binding_commit}.items():
        if not commit:
            findings.append(f"{label.upper()}_COMMIT_MISSING")
        elif not commit_exists(commit):
            findings.append(f"{label.upper()}_COMMIT_NOT_FOUND")
    if findings:
        return findings

    if candidate == manifest_commit or candidate == binding_commit or manifest_commit == binding_commit:
        findings.append("FREEZE_COMMITS_NOT_DISTINCT")
    if not is_ancestor(candidate, manifest_commit):
        findings.append("CANDIDATE_NOT_ANCESTOR_OF_MANIFEST")
    if not is_ancestor(manifest_commit, binding_commit):
        findings.append("MANIFEST_NOT_ANCESTOR_OF_BINDING")
    if not is_ancestor(binding_commit, head):
        findings.append("BINDING_NOT_ANCESTOR_OF_HEAD")
    if changed_files(manifest_commit) != [MANIFEST_REL]:
        findings.append("MANIFEST_COMMIT_CHANGED_UNEXPECTED_FILES")
    if changed_files(binding_commit) != [BINDING_REL]:
        findings.append("BINDING_COMMIT_CHANGED_UNEXPECTED_FILES")

    try:
        manifest_bytes = git_bytes(manifest_commit, MANIFEST_REL)
        manifest = json.loads(manifest_bytes)
    except Exception:
        findings.append("FREEZE_MANIFEST_NOT_READABLE_AT_MANIFEST_COMMIT")
        return findings
    if git_blob(manifest_commit, MANIFEST_REL) != binding.get("freeze_manifest_blob_sha"):
        findings.append("FREEZE_MANIFEST_BLOB_SHA_MISMATCH")
    if sha256_bytes(manifest_bytes) != binding.get("freeze_manifest_sha256"):
        findings.append("FREEZE_MANIFEST_SHA256_MISMATCH")
    if logical_hash(binding, "freeze_binding_logical_hash") != binding.get("freeze_binding_logical_hash"):
        findings.append("FREEZE_BINDING_LOGICAL_HASH_MISMATCH")
    if logical_hash(manifest, "manifest_logical_hash") != manifest.get("manifest_logical_hash"):
        findings.append("FREEZE_MANIFEST_LOGICAL_HASH_MISMATCH")
    if git("show", "-s", "--format=%T", candidate) != manifest.get("freeze_candidate_tree_hash"):
        findings.append("FREEZE_CANDIDATE_TREE_HASH_MISMATCH")

    inventory = manifest.get("frozen_files") or []
    registered = {entry.get("path") for entry in inventory}
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
        if git_blob(candidate, path) != entry.get("blob_sha_at_candidate"):
            findings.append(f"FROZEN_BLOB_SHA_MISMATCH:{path}")
        if sha256_bytes(candidate_bytes) != entry.get("sha256_at_candidate"):
            findings.append(f"FROZEN_SHA256_MISMATCH:{path}")
        final_path = ROOT / path
        if entry.get("required_at_final_head", True) and not final_path.exists():
            findings.append(f"FROZEN_FILE_MISSING_AT_FINAL_HEAD:{path}")
        elif final_path.exists() and final_path.read_bytes() != candidate_bytes:
            findings.append(f"FROZEN_FILE_CHANGED_AFTER_CANDIDATE:{path}")

    for directory in manifest.get("frozen_directories", []):
        candidate_files = files_under_git(candidate, directory)
        final_files = {
            str(path.relative_to(ROOT))
            for path in (ROOT / directory).rglob("*")
            if path.is_file() and "__pycache__" not in str(path) and not path.name.endswith(".pyc")
        }
        if candidate_files != final_files:
            findings.append(f"FROZEN_DIRECTORY_MEMBERSHIP_CHANGED:{directory}")
        for path in final_files:
            if path not in registered:
                findings.append(f"UNREGISTERED_FROZEN_DIRECTORY_FILE:{path}")

    if manifest_path:
        campaign = load(manifest_path)
        required = [
            "campaign_execution_sha",
            "workflow_head_sha",
            "freeze_candidate_sha",
            "freeze_manifest_commit_sha",
            "freeze_binding_commit_sha",
            "freeze_manifest_blob_sha",
            "freeze_manifest_sha256",
            "internal_payload_manifest_hash",
        ]
        for key in required:
            if key not in campaign:
                findings.append(f"CAMPAIGN_MANIFEST_FIELD_MISSING:{key}")
        if campaign.get("campaign_execution_sha") != campaign.get("workflow_head_sha"):
            findings.append("EXECUTION_SHA_WORKFLOW_HEAD_MISMATCH")
        if campaign.get("freeze_binding_commit_sha") != binding_commit:
            findings.append("CAMPAIGN_FREEZE_BINDING_COMMIT_MISMATCH")
        if campaign.get("freeze_manifest_commit_sha") != manifest_commit:
            findings.append("CAMPAIGN_FREEZE_MANIFEST_COMMIT_MISMATCH")
        if campaign.get("freeze_manifest_blob_sha") != binding.get("freeze_manifest_blob_sha"):
            findings.append("CAMPAIGN_FREEZE_MANIFEST_BLOB_MISMATCH")
        if campaign.get("freeze_manifest_sha256") != binding.get("freeze_manifest_sha256"):
            findings.append("CAMPAIGN_FREEZE_MANIFEST_SHA256_MISMATCH")
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        if not payload_path.exists():
            findings.append("INTERNAL_PAYLOAD_MANIFEST_MISSING")
        else:
            payload = load(payload_path)
            if payload.get("freeze_binding_commit_sha") != binding_commit:
                findings.append("PAYLOAD_FREEZE_BINDING_MISMATCH")
            if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
                findings.append("INTERNAL_PAYLOAD_HASH_NOT_REPRODUCIBLE")
            if campaign.get("internal_payload_manifest_hash") != payload.get("aggregate_payload_hash"):
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
