#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

DEFAULT_ROOTS = [
    Path("artifacts/capability-runtime"),
    Path("docs/capability"),
]
FROZEN_CASE_MANIFEST = ROOT / "benchmarks" / "capability_genesis_v5" / "manifests" / "frozen_case_manifest.json"

TOTAL_CAP_USD = 3.00
MAX_CASES = 24
TERMINAL_COUNT_FIELDS = {
    "completed_cases": "COMPLETED",
    "failed_cases": "FAILED",
    "timed_out_cases": "TIMED_OUT",
    "denied_cases": "DENIED",
    "evidence_unavailable_cases": "EVIDENCE_UNAVAILABLE",
    "evaluator_unavailable_cases": "EVALUATOR_UNAVAILABLE",
    "invalid_response_cases": "INVALID_RESPONSE",
    "infrastructure_failure_cases": "INFRASTRUCTURE_FAILURE",
}
TERMINAL_STATUSES = set(TERMINAL_COUNT_FIELDS.values())
FROZEN_EXECUTION_SPLITS = {"validation", "hidden"}


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


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _case_requires_diagnosable_provider_evidence(record: dict[str, Any]) -> bool:
    if record.get("terminal_status") == "EVIDENCE_UNAVAILABLE":
        return False
    if record.get("terminal_status") in {"COMPLETED", "INVALID_RESPONSE", "EVALUATOR_UNAVAILABLE"}:
        return True
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


def _case_semantic_hash(record: dict[str, Any]) -> str:
    fields = [
        "campaign_id",
        "case_id",
        "domain",
        "terminal_status",
        "failure_category",
        "requested_model",
        "returned_model_identity",
        "redacted_request_hash",
        "provider_response_hash",
        "finish_reason",
        "parser_input_hash",
        "usage",
        "cost",
        "evaluator_result",
    ]
    return _sha256_text(_canonical({key: record.get(key) for key in fields}))


def _aggregate_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record.get("terminal_status") == "COMPLETED"]
    scored = [record for record in completed if isinstance(record.get("evaluator_result"), dict) and record["evaluator_result"].get("scorable") is True]
    scores = [float(record["evaluator_result"]["score"]) for record in scored]
    domain_report: dict[str, Any] = {}
    supported: list[str] = []
    for domain in sorted({record.get("domain") for record in records if record.get("domain")}):
        domain_records = [record for record in records if record.get("domain") == domain]
        domain_completed = [record for record in domain_records if record.get("terminal_status") == "COMPLETED"]
        domain_scored = [
            record
            for record in domain_completed
            if isinstance(record.get("evaluator_result"), dict) and record["evaluator_result"].get("scorable") is True
        ]
        domain_scores = [float(record["evaluator_result"]["score"]) for record in domain_scored]
        mean = round(sum(domain_scores) / len(domain_scores), 6) if domain_scores else None
        threshold_passed = bool(domain_scored) and mean is not None and mean >= 0.6 and len(domain_scored) == len(domain_records)
        if threshold_passed:
            supported.append(domain)
        domain_report[domain] = {
            "planned_cases": len(domain_records),
            "executed_cases": len(domain_records),
            "completed_cases": len(domain_completed),
            "scored_cases": len(domain_scored),
            "mean_correctness": mean,
            "threshold_verdict": "passed" if threshold_passed else "not_established",
        }
    return {
        "completed": len(completed),
        "scored": len(scored),
        "aggregate_correctness": round(sum(scores) / len(scores), 6) if scores else None,
        "domain_report": domain_report,
        "supported_domains": supported,
    }


def _recompute_decision(manifest: dict[str, Any], records: list[dict[str, Any]], rolled: dict[str, Any]) -> str:
    if len(records) != MAX_CASES:
        return "INVALID_CAMPAIGN"
    actual_spend = manifest.get("total_campaign_cost_usd") or 0
    if actual_spend > TOTAL_CAP_USD:
        return "INVALID_CAMPAIGN"
    if any(record.get("cost", {}).get("unreleased_amount") != 0 for record in records):
        return "INVALID_CAMPAIGN"
    if rolled["completed"] < 18 or rolled["scored"] < 18:
        return "HOLD_FOR_MORE_EVIDENCE"
    if (rolled["aggregate_correctness"] or 0) >= 0.70 and len(rolled["supported_domains"]) >= 8:
        return "REAL_CAPABILITY_BASELINE_ACCEPTED"
    return "REAL_CAPABILITY_BASELINE_REJECTED"


def _aggregate_semantic_hash(manifest: dict[str, Any]) -> str:
    volatile_or_late_bound = {"generated_at", "semantic_hash", "internal_payload_manifest_hash"}
    return _sha256_text(_canonical({key: value for key, value in manifest.items() if key not in volatile_or_late_bound}))


def _load_expected_case_population(path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    findings: list[str] = []
    try:
        manifest = load(path)
    except (OSError, ValueError) as exc:
        return {}, [f"GENESIS_V7_FROZEN_CASE_MANIFEST_INVALID:{path}:{type(exc).__name__}"]
    if not isinstance(manifest, dict):
        return {}, [f"GENESIS_V7_FROZEN_CASE_MANIFEST_NOT_OBJECT:{path}"]
    cases = manifest.get("cases")
    if not isinstance(cases, list):
        return {}, [f"GENESIS_V7_FROZEN_CASE_MANIFEST_CASES_INVALID:{path}"]
    expected: dict[str, dict[str, str]] = {}
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            findings.append(f"GENESIS_V7_FROZEN_CASE_RECORD_NOT_OBJECT:{path}:index={index}")
            continue
        split = case.get("split")
        if split not in FROZEN_EXECUTION_SPLITS:
            continue
        case_id = case.get("case_id")
        domain = case.get("domain")
        if not isinstance(case_id, str) or not isinstance(domain, str):
            findings.append(f"GENESIS_V7_FROZEN_CASE_RECORD_INVALID:{path}:index={index}")
            continue
        if case_id in expected:
            findings.append(f"GENESIS_V7_FROZEN_CASE_DUPLICATE:{path}:{case_id}")
        expected[case_id] = {"split": split, "domain": domain}
    if len(expected) != MAX_CASES:
        findings.append(f"GENESIS_V7_FROZEN_CASE_COUNT_MISMATCH:{path}:expected={MAX_CASES}:actual={len(expected)}")
    return expected, findings


def _verify_case_population(
    manifest_path: Path,
    case_records: list[dict[str, Any]],
    frozen_case_manifest_path: Path,
) -> list[str]:
    expected_cases, findings = _load_expected_case_population(frozen_case_manifest_path)
    if findings:
        return findings
    observed_ids = {record.get("case_id") for record in case_records if isinstance(record.get("case_id"), str)}
    expected_ids = set(expected_cases)
    for case_id in sorted(expected_ids - observed_ids):
        findings.append(f"GENESIS_V7_FROZEN_CASE_MISSING:{manifest_path}:{case_id}")
    for case_id in sorted(observed_ids - expected_ids):
        findings.append(f"GENESIS_V7_UNREGISTERED_CASE_RECORD:{manifest_path}:{case_id}")
    for record in case_records:
        case_id = record.get("case_id")
        if case_id not in expected_cases:
            continue
        expected = expected_cases[case_id]
        if record.get("split") != expected["split"]:
            findings.append(
                f"GENESIS_V7_CASE_SPLIT_MISMATCH:{manifest_path}:{case_id}:expected={expected['split']}:actual={record.get('split')}"
            )
        if record.get("domain") != expected["domain"]:
            findings.append(
                f"GENESIS_V7_CASE_DOMAIN_MISMATCH:{manifest_path}:{case_id}:expected={expected['domain']}:actual={record.get('domain')}"
            )
    return findings


def verify_genesis_v7_evidence(
    manifest_path: Path,
    manifest: dict[str, Any],
    frozen_case_manifest_path: Path | None = None,
) -> list[str]:
    findings: list[str] = []
    if manifest.get("artifact_type") != "real_provider_genesis_v7_aggregate":
        return findings

    case_paths = sorted(manifest_path.parent.glob("CASE_*.json"))
    case_records: list[dict[str, Any]] = []
    for case_path in case_paths:
        try:
            record = load(case_path)
        except (OSError, ValueError) as exc:
            findings.append(f"GENESIS_V7_CASE_JSON_INVALID:{case_path}:{type(exc).__name__}")
            continue
        if not isinstance(record, dict):
            findings.append(f"GENESIS_V7_CASE_RECORD_NOT_OBJECT:{case_path}")
            continue
        case_id = record.get("case_id")
        expected_case_id = case_path.name.removeprefix("CASE_").removesuffix(".json")
        if case_id != expected_case_id:
            findings.append(f"GENESIS_V7_CASE_ID_FILENAME_MISMATCH:{case_path}:case_id={case_id}:filename={expected_case_id}")
        if record.get("campaign_id") != manifest.get("campaign_id"):
            findings.append(f"GENESIS_V7_CASE_CAMPAIGN_ID_MISMATCH:{case_path}:case={record.get('campaign_id')}:manifest={manifest.get('campaign_id')}")
        if record.get("terminal_status") not in TERMINAL_STATUSES:
            findings.append(f"GENESIS_V7_UNKNOWN_TERMINAL_STATUS:{case_path}:{record.get('terminal_status')}")
        case_records.append(record)

    case_ids = [record.get("case_id") for record in case_records]
    for case_id in sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1}):
        findings.append(f"GENESIS_V7_DUPLICATE_CASE_ID:{manifest_path}:{case_id}")

    executed_cases = manifest.get("executed_cases")
    if executed_cases is not None and executed_cases != len(case_records):
        findings.append(f"GENESIS_V7_CASE_TOTAL_MISMATCH:{manifest_path}:manifest={executed_cases}:files={len(case_records)}")

    manifest_semantic_hash = manifest.get("semantic_hash")
    recomputed_manifest_semantic_hash = _aggregate_semantic_hash(manifest)
    if not _is_sha256(manifest_semantic_hash):
        findings.append(f"GENESIS_V7_AGGREGATE_SEMANTIC_HASH_MISSING:{manifest_path}")
    elif manifest_semantic_hash != recomputed_manifest_semantic_hash:
        findings.append(f"GENESIS_V7_AGGREGATE_SEMANTIC_HASH_MISMATCH:{manifest_path}")

    if manifest.get("baseline_execution_attempted") is False:
        if case_records:
            findings.append(f"GENESIS_V7_HOLD_HAS_CASE_RECORDS:{manifest_path}:count={len(case_records)}")
        if manifest.get("decision") != "HOLD_FOR_MORE_EVIDENCE":
            findings.append(f"GENESIS_V7_HOLD_DECISION_MISMATCH:{manifest_path}:decision={manifest.get('decision')}")
        planned = manifest.get("planned_cases", MAX_CASES)
        if manifest.get("evidence_unavailable_cases") != planned:
            findings.append(
                f"GENESIS_V7_HOLD_EVIDENCE_UNAVAILABLE_MISMATCH:{manifest_path}:expected={planned}:actual={manifest.get('evidence_unavailable_cases')}"
            )
        for field in (
            "completed_cases",
            "failed_cases",
            "timed_out_cases",
            "denied_cases",
            "evaluator_unavailable_cases",
            "invalid_response_cases",
            "infrastructure_failure_cases",
        ):
            if manifest.get(field, 0) != 0:
                findings.append(f"GENESIS_V7_HOLD_TERMINAL_COUNT_NONZERO:{manifest_path}:{field}={manifest.get(field)}")
        return findings

    if frozen_case_manifest_path is not None:
        findings.extend(_verify_case_population(manifest_path, case_records, frozen_case_manifest_path))

    required_count_fields = ["planned_cases", "executed_cases", *TERMINAL_COUNT_FIELDS]
    for field in required_count_fields:
        if field not in manifest:
            findings.append(f"GENESIS_V7_REQUIRED_COUNT_FIELD_MISSING:{manifest_path}:{field}")
    for aggregate_field, status in TERMINAL_COUNT_FIELDS.items():
        expected = manifest.get(aggregate_field)
        if expected is None:
            continue
        actual = sum(1 for record in case_records if record.get("terminal_status") == status)
        if expected != actual:
            findings.append(f"GENESIS_V7_TERMINAL_TOTAL_MISMATCH:{manifest_path}:{aggregate_field}:manifest={expected}:files={actual}")
    terminal_bucket_total = sum(sum(1 for record in case_records if record.get("terminal_status") == status) for status in TERMINAL_STATUSES)
    if terminal_bucket_total != len(case_records):
        findings.append(f"GENESIS_V7_TERMINAL_BUCKET_TOTAL_MISMATCH:{manifest_path}:bucketed={terminal_bucket_total}:records={len(case_records)}")

    for record in case_records:
        expected_hash = record.get("semantic_hash")
        actual_hash = _case_semantic_hash(record)
        if not _is_sha256(expected_hash):
            findings.append(f"GENESIS_V7_CASE_SEMANTIC_HASH_MISSING:{manifest_path}:{record.get('case_id')}")
        elif expected_hash != actual_hash:
            findings.append(f"GENESIS_V7_CASE_SEMANTIC_HASH_MISMATCH:{manifest_path}:{record.get('case_id')}")

    rolled = _aggregate_records(case_records)
    if manifest.get("aggregate_correctness") != rolled["aggregate_correctness"]:
        findings.append(
            f"GENESIS_V7_AGGREGATE_CORRECTNESS_MISMATCH:{manifest_path}:manifest={manifest.get('aggregate_correctness')}:files={rolled['aggregate_correctness']}"
        )
    if sorted(manifest.get("supported_domains") or []) != rolled["supported_domains"]:
        findings.append(f"GENESIS_V7_SUPPORTED_DOMAINS_MISMATCH:{manifest_path}")
    expected_decision = _recompute_decision(manifest, case_records, rolled)
    if manifest.get("decision") != expected_decision:
        findings.append(f"GENESIS_V7_DECISION_MISMATCH:{manifest_path}:manifest={manifest.get('decision')}:recomputed={expected_decision}")

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


def verify_artifacts(root: Path, frozen_case_manifest_path: Path | None = FROZEN_CASE_MANIFEST) -> list[str]:
    findings: list[str] = []
    manifests = find_manifests(root)
    if not manifests:
        findings.append("NO_CAPABILITY_GENESIS_ARTIFACT_MANIFEST")
    for manifest_path in manifests:
        try:
            manifest = load(manifest_path)
        except (OSError, ValueError) as exc:
            findings.append(f"CAPABILITY_MANIFEST_JSON_INVALID:{manifest_path}:{type(exc).__name__}")
            continue
        if not isinstance(manifest, dict):
            findings.append(f"CAPABILITY_MANIFEST_NOT_OBJECT:{manifest_path}")
            continue
        payload_path = manifest_path.parent / "INTERNAL_PAYLOAD_MANIFEST.json"
        payload = None
        if not payload_path.exists():
            findings.append(f"PAYLOAD_MANIFEST_MISSING:{manifest_path}")
        else:
            try:
                payload = load(payload_path)
            except (OSError, ValueError) as exc:
                findings.append(f"PAYLOAD_MANIFEST_JSON_INVALID:{manifest_path}:{type(exc).__name__}")
                payload = None
            if payload is not None and not isinstance(payload, dict):
                findings.append(f"PAYLOAD_MANIFEST_NOT_OBJECT:{manifest_path}")
                payload = None
        if payload is not None:
            if reproduce_payload_hash(payload, manifest_path.parent) != payload.get("aggregate_payload_hash"):
                findings.append(f"PAYLOAD_HASH_MISMATCH:{manifest_path}")
            if manifest.get("internal_payload_manifest_hash") != payload.get("aggregate_payload_hash"):
                findings.append(f"MANIFEST_PAYLOAD_HASH_MISMATCH:{manifest_path}")
        if manifest.get("campaign_execution_sha") != manifest.get("workflow_head_sha"):
            findings.append(f"SHA_BINDING_MISMATCH:{manifest_path}")
        if manifest.get("campaign_id") in CURRENT_FREEZE_CAMPAIGNS:
            findings.extend(verify_manifest(manifest_path))
        findings.extend(verify_genesis_v7_evidence(manifest_path, manifest, frozen_case_manifest_path=frozen_case_manifest_path))
    return findings


def verify_roots(roots: list[Path], frozen_case_manifest_path: Path | None = FROZEN_CASE_MANIFEST) -> list[str]:
    findings: list[str] = []
    seen: set[str] = set()
    for root in roots:
        for finding in verify_artifacts(root, frozen_case_manifest_path=frozen_case_manifest_path):
            if finding not in seen:
                seen.add(finding)
                findings.append(finding)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--root",
        action="append",
        help="Artifact/evidence root to verify. May be supplied multiple times. Defaults to local artifacts and committed docs evidence.",
    )
    args = parser.parse_args()
    roots = [ROOT / root for root in (args.root or DEFAULT_ROOTS)]
    findings = verify_roots(roots)
    print(json.dumps({"success": not findings, "findings": findings}, indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
