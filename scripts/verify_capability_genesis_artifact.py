#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import reproduce_payload_hash  # noqa: E402
from scripts.verify_capability_genesis_freeze import verify_manifest  # noqa: E402


def load(path: Path):
    return json.loads(path.read_text())


def find_manifests(root: Path) -> list[Path]:
    return list(root.glob("**/PROTOCOL_BASELINE_MANIFEST.json")) + list(root.glob("**/GENESIS_V3_MANIFEST.json"))


def verify_artifacts(root: Path) -> list[str]:
    findings: list[str] = []
    manifests = find_manifests(root)
    if not manifests:
        findings.append("NO_CAPABILITY_GENESIS_ARTIFACT_MANIFEST")
    for manifest_path in manifests:
        manifest = load(manifest_path)
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        if not payload_path.exists():
            findings.append(f"PAYLOAD_MANIFEST_MISSING:{manifest_path}")
            continue
        payload = load(payload_path)
        if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
            findings.append(f"PAYLOAD_HASH_MISMATCH:{manifest_path}")
        if manifest.get("internal_payload_manifest_hash") != payload.get("aggregate_payload_hash"):
            findings.append(f"MANIFEST_PAYLOAD_HASH_MISMATCH:{manifest_path}")
        if manifest.get("campaign_execution_sha") != manifest.get("workflow_head_sha"):
            findings.append(f"SHA_BINDING_MISMATCH:{manifest_path}")
        findings.extend(verify_manifest(manifest_path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", default="artifacts/capability-runtime")
    args = parser.parse_args()
    findings = verify_artifacts(ROOT / args.root)
    print(json.dumps({"success": not findings, "findings": findings}, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
