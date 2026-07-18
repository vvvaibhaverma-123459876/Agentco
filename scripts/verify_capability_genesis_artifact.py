#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentco_capability.evidence import reproduce_payload_hash  # noqa: E402
from scripts.verify_capability_genesis_freeze import verify_manifest  # noqa: E402


CURRENT_FREEZE_CAMPAIGNS = {
    "governed-capability-protocol-baseline-v3",
    "governed-capability-genesis-v5",
}


def load(path: Path):
    return json.loads(path.read_text())


def find_manifests(root: Path) -> list[Path]:
    return (
        list(root.glob("**/PROTOCOL_BASELINE_MANIFEST.json"))
        + list(root.glob("**/GENESIS_V3_MANIFEST.json"))
        + list(root.glob("**/GENESIS_V4_MANIFEST.json"))
        + list(root.glob("**/GENESIS_V5_MANIFEST.json"))
        + list(root.glob("**/GENESIS_V7_CAMPAIGN_MANIFEST.json"))
    )


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _case_requires_diagnosable_provider_evidence(record: dict[str, Any]) -> bool:
    if record.get("terminal_status") == "EVIDENCE_UNAVAILABLE":
        return False
    return bool(
        record.get("provider_request_id_captured")
        or record.get("provider_response_hash")
        or record.get("returned_model_identity")
    )


def _has_diagnosable_provider_evidence(record: dict[str, Any]) -> bool:
    return bool(
        _is_sha256(record.get("provider_response_hash"))
        and isinstance(record.get("redacted_provider_response"), dict)
        and _is_sha256(record.get("provider_request_id_hash"))
        and record.get("finish_reason") is not None
        and _is_sha256(record.get("parser_input_hash"))
        and record.get("parser_input_redacted") is not None
        and record.get("audit_references")
    )


def verify_genesis_v7_evidence(manifest_path: Path, manifest: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    if manifest.get("artifact_type") != "real_provider_genesis_v7_aggregate":
        return findings

    case_paths = sorted(manifest_path.parent.glob("CASE_*.json"))
    case_records: list[dict[str, Any]] = []
    for case_path in case_paths:
        try:
            case_records.append(load(case_path))
        except json.JSONDecodeError as exc:
            findings.append(f"GENESIS_V7_CASE_JSON_INVALID:{case_path}:{exc.msg}")

    executed_cases = manifest.get("executed_cases")
    if executed_cases is not None and executed_cases != len(case_records):
        findings.append(f"GENESIS_V7_CASE_TOTAL_MISMATCH:{manifest_path}:manifest={executed_cases}:files={len(case_records)}")

    terminal_statuses = {
        "completed_cases": "COMPLETED",
        "failed_cases": "FAILED",
        "timed_out_cases": "TIMED_OUT",
        "denied_cases": "DENIED",
        "evidence_unavailable_cases": "EVIDENCE_UNAVAILABLE",
        "evaluator_unavailable_cases": "EVALUATOR_UNAVAILABLE",
        "invalid_response_cases": "INVALID_RESPONSE",
        "infrastructure_failure_cases": "INFRASTRUCTURE_FAILURE",
    }
    for aggregate_field, status in terminal_statuses.items():
        expected = manifest.get(aggregate_field)
        if expected is None:
            continue
        actual = sum(1 for record in case_records if record.get("terminal_status") == status)
        if expected != actual:
            findings.append(f"GENESIS_V7_TERMINAL_TOTAL_MISMATCH:{manifest_path}:{aggregate_field}:manifest={expected}:files={actual}")

    for record in case_records:
        if _case_requires_diagnosable_provider_evidence(record) and not _has_diagnosable_provider_evidence(record):
            findings.append(f"GENESIS_V7_PROVIDER_EVIDENCE_NOT_DIAGNOSABLE:{manifest_path}:{record.get('case_id')}")

    response_hashes = [
        record.get("provider_response_hash")
        for record in case_records
        if _case_requires_diagnosable_provider_evidence(record) and _is_sha256(record.get("provider_response_hash"))
    ]
    if len(response_hashes) > 1 and len(set(response_hashes)) == 1:
        findings.append(f"GENESIS_V7_IDENTICAL_PROVIDER_RESPONSE_HASHES:{manifest_path}:count={len(response_hashes)}")

    if manifest.get("decision") in {"REAL_CAPABILITY_BASELINE_ACCEPTED", "REAL_CAPABILITY_BASELINE_REJECTED"}:
        if manifest.get("completed_cases", 0) <= 0 or manifest.get("aggregate_correctness") is None:
            findings.append(f"GENESIS_V7_DECISION_WITHOUT_SCORABLE_COMPLETIONS:{manifest_path}")
        if manifest.get("supported_domains") and manifest.get("aggregate_correctness") is None:
            findings.append(f"GENESIS_V7_SUPPORTED_DOMAINS_WITHOUT_CORRECTNESS:{manifest_path}")

    return findings


def verify_artifacts(root: Path) -> list[str]:
    findings: list[str] = []
    manifests = find_manifests(root)
    if not manifests:
        findings.append("NO_CAPABILITY_GENESIS_ARTIFACT_MANIFEST")
    for manifest_path in manifests:
        manifest = load(manifest_path)
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        payload = None
        if not payload_path.exists():
            findings.append(f"PAYLOAD_MANIFEST_MISSING:{manifest_path}")
        else:
            payload = load(payload_path)
            if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
                findings.append(f"PAYLOAD_HASH_MISMATCH:{manifest_path}")
            if manifest.get("internal_payload_manifest_hash") != payload.get("aggregate_payload_hash"):
                findings.append(f"MANIFEST_PAYLOAD_HASH_MISMATCH:{manifest_path}")
        if manifest.get("campaign_execution_sha") != manifest.get("workflow_head_sha"):
            findings.append(f"SHA_BINDING_MISMATCH:{manifest_path}")
        if manifest.get("campaign_id") in CURRENT_FREEZE_CAMPAIGNS:
            findings.extend(verify_manifest(manifest_path))
        findings.extend(verify_genesis_v7_evidence(manifest_path, manifest))
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
