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

from agentco_capability.evidence import bundle_hash, canonical_json, files_under, git  # noqa: E402

DOCS = ROOT / "docs" / "audit" / "current"
MANIFEST_PATH = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_MANIFEST.json"
BINDING_PATH = DOCS / "GOVERNED_CAPABILITY_GENESIS_V5_FREEZE_BINDING.json"

FROZEN_DIRECTORIES = [
    ".github/workflows",
    "agentco_capability",
    "benchmarks/capability_protocol_baseline_v3",
    "benchmarks/capability_genesis_v5",
    "schemas",
]

FROZEN_FILES = [
    "Makefile",
    "requirements/requirements.lock.txt",
    "scripts/create_capability_genesis_freeze.py",
    "scripts/run_governed_capability_genesis.py",
    "scripts/verify_capability_genesis_artifact.py",
    "scripts/verify_capability_genesis_freeze.py",
    "tests/test_capability_freeze_binding.py",
    "tests/test_capability_freeze_integrity.py",
    "tests/test_capability_genesis_v5.py",
    "tests/test_protocol_baseline_v3.py",
    "tests/test_protocol_schema_validation.py",
    "tests/test_protocol_persistence_reinitialization.py",
    "tests/test_protocol_secret_redaction.py",
    "tests/test_protocol_budget_settlement.py",
    "tests/test_capability_preflight.py",
    "tests/test_software_capability_workspace.py",
    "tests/test_data_capability_workspace.py",
    "tests/test_capability_anti_hardcoding.py",
    "tests/test_domain_scorers.py",
    "tests/test_capability_provider_adapters.py",
    "tests/test_capability_runtime.py",
]


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_blob(commit: str, path: str) -> str:
    return git("rev-parse", f"{commit}:{path}")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_files(commit: str, directory: str) -> list[str]:
    output = git("ls-tree", "-r", "--name-only", commit, directory)
    return [line for line in output.splitlines() if line.strip() and "__pycache__" not in line and not line.endswith(".pyc")]


def inventory(candidate: str) -> list[dict[str, Any]]:
    paths = set(FROZEN_FILES)
    for directory in FROZEN_DIRECTORIES:
        paths.update(git_files(candidate, directory))
    rows = []
    for path in sorted(paths):
        data = git_bytes(candidate, path)
        rows.append(
            {
                "path": path,
                "blob_sha_at_candidate": git_blob(candidate, path),
                "sha256_at_candidate": sha256(data),
                "size_bytes_at_candidate": len(data),
                "bundle": bundle_for(path),
                "required_at_final_head": True,
            }
        )
    return rows


def bundle_for(path: str) -> str:
    if path.startswith(".github/workflows"):
        return "workflow_execution_logic"
    if path.startswith("agentco_capability/providers"):
        return "providers"
    if path.startswith("agentco_capability/tools"):
        return "tools"
    if path.startswith("agentco_capability/scoring"):
        return "scorers"
    if path.startswith("agentco_capability"):
        return "runtime"
    if path.startswith("benchmarks/capability_protocol_baseline_v3"):
        return "protocol_benchmark"
    if path.startswith("benchmarks/capability_genesis_v5/rubrics"):
        return "rubrics"
    if path.startswith("benchmarks/capability_genesis_v5/fixtures"):
        return "fixtures"
    if path.startswith("benchmarks/capability_genesis_v5"):
        return "real_benchmark"
    if path.startswith("schemas"):
        return "schemas"
    if path.startswith("scripts/verify_capability_genesis_freeze"):
        return "freeze_verifier"
    if path.startswith("scripts/verify_capability_genesis_artifact"):
        return "artifact_verifier"
    if path.startswith("scripts/run_governed_capability_genesis"):
        return "evaluator_runner"
    if path.startswith("tests"):
        return "tests"
    if "lock" in path:
        return "dependency_locks"
    return "acceptance_thresholds"


def logical_hash(data: dict[str, Any], field: str) -> str:
    clean = dict(data)
    clean.pop(field, None)
    return hashlib.sha256(canonical_json(clean).encode()).hexdigest()


def write_manifest(candidate: str) -> None:
    rows = inventory(candidate)
    by_bundle: dict[str, list[Path]] = {}
    for row in rows:
        by_bundle.setdefault(row["bundle"], []).append(ROOT / row["path"])
    data: dict[str, Any] = {
        "freeze_schema_version": "governed-capability-genesis-v5-freeze-manifest-v1",
        "freeze_candidate_sha": candidate,
        "freeze_candidate_tree_hash": git("show", "-s", "--format=%T", candidate),
        "protocol_campaign_id": "governed-capability-protocol-baseline-v3",
        "real_capability_campaign_id": "governed-capability-genesis-v5",
        "acceptance_thresholds": {
            "protocol_requires_all_predicates": True,
            "real_provider_requires_scored_execution": True,
            "provider_unavailable_decision": "HOLD_FOR_MORE_EVIDENCE",
        },
        "frozen_directories": FROZEN_DIRECTORIES,
        "frozen_files": rows,
        "bundle_hashes": {name: bundle_hash(paths) for name, paths in sorted(by_bundle.items())},
        "manifest_logical_hash": "",
    }
    data["manifest_logical_hash"] = logical_hash(data, "manifest_logical_hash")
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(canonical_json(data))


def write_binding(manifest_commit: str) -> None:
    manifest_bytes = git_bytes(manifest_commit, str(MANIFEST_PATH.relative_to(ROOT)))
    data: dict[str, Any] = {
        "freeze_schema_version": "governed-capability-genesis-v5-freeze-binding-v1",
        "freeze_candidate_sha": json.loads(manifest_bytes)["freeze_candidate_sha"],
        "freeze_manifest_commit_sha": manifest_commit,
        "freeze_manifest_blob_sha": git_blob(manifest_commit, str(MANIFEST_PATH.relative_to(ROOT))),
        "freeze_manifest_sha256": sha256(manifest_bytes),
        "freeze_binding_logical_hash": "",
    }
    data["freeze_binding_logical_hash"] = logical_hash(data, "freeze_binding_logical_hash")
    BINDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    BINDING_PATH.write_text(canonical_json(data))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["manifest", "binding"])
    parser.add_argument("--candidate")
    parser.add_argument("--manifest-commit")
    args = parser.parse_args()
    if args.mode == "manifest":
        if not args.candidate:
            raise SystemExit("--candidate is required")
        write_manifest(args.candidate)
    else:
        if not args.manifest_commit:
            raise SystemExit("--manifest-commit is required")
        write_binding(args.manifest_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
