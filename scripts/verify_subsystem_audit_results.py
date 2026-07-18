#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_PATH = ROOT / "docs" / "audit" / "current" / "SUBSYSTEM_AUDIT_RESULTS.json"

REQUIRED_SUBSYSTEMS = [
    "l0_runtime_substrate",
    "l1_identity_authority",
    "l2_resource_budgeting",
    "l3_event_memory",
    "l4_evidence_retrieval",
    "l5_claim_prediction",
    "l6_calibration_trust",
    "l7_agent_citizenship",
    "l8_autonomy_tasks",
    "l9_institutions",
    "l10_governance_safety",
    "l11_judiciary",
    "l12_learning_memory",
    "l13_capability_expansion",
    "l14_civilization_os",
    "capability_runtime_protocol",
    "frontend",
    "infra_deployment",
]

BLOCKING_FINDING_STATUSES = {"open_blocking", "open_hold_for_more_evidence"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _subsystem_entries(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = payload.get("subsystems")
    if isinstance(raw, dict):
        return {str(key): value for key, value in raw.items() if isinstance(value, dict)}
    if isinstance(raw, list):
        entries: dict[str, dict[str, Any]] = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            subsystem_id = item.get("subsystem_id") or item.get("id")
            if subsystem_id:
                entries[str(subsystem_id)] = item
        return entries
    return {}


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and value > 0


def _nonempty_list(value: object) -> bool:
    return isinstance(value, list) and bool(value)


def verify_results(path: Path = DEFAULT_RESULTS_PATH) -> list[str]:
    findings: list[str] = []
    if not path.exists():
        return [f"SUBSYSTEM_AUDIT_RESULTS_MISSING:{path}"]

    try:
        payload = load_json(path)
    except json.JSONDecodeError as exc:
        return [f"SUBSYSTEM_AUDIT_RESULTS_INVALID_JSON:{path}:{exc.msg}"]

    if not isinstance(payload, dict):
        return [f"SUBSYSTEM_AUDIT_RESULTS_INVALID_SHAPE:{path}"]

    entries = _subsystem_entries(payload)
    for subsystem_id in REQUIRED_SUBSYSTEMS:
        entry = entries.get(subsystem_id)
        if entry is None:
            findings.append(f"SUBSYSTEM_AUDIT_MISSING:{subsystem_id}")
            continue
        if entry.get("audit_status") != "passed":
            findings.append(f"SUBSYSTEM_AUDIT_NOT_PASSED:{subsystem_id}:{entry.get('audit_status')}")
        if entry.get("tool_exit_code") != 0:
            findings.append(f"SUBSYSTEM_AUDIT_NONZERO_EXIT:{subsystem_id}:{entry.get('tool_exit_code')}")
        if not _positive_int(entry.get("agent_output_tokens")):
            findings.append(f"SUBSYSTEM_AUDIT_ZERO_OUTPUT_TOKENS:{subsystem_id}")
        if not entry.get("started_at") or not entry.get("completed_at"):
            findings.append(f"SUBSYSTEM_AUDIT_MISSING_TIMESTAMPS:{subsystem_id}")
        if not _nonempty_list(entry.get("evidence_paths")):
            findings.append(f"SUBSYSTEM_AUDIT_MISSING_EVIDENCE:{subsystem_id}")
        for item in entry.get("findings", []) if isinstance(entry.get("findings"), list) else []:
            if isinstance(item, dict) and item.get("status") in BLOCKING_FINDING_STATUSES:
                findings.append(f"SUBSYSTEM_AUDIT_OPEN_FINDING:{subsystem_id}:{item.get('finding_id', 'UNKNOWN')}")

    extra = sorted(set(entries) - set(REQUIRED_SUBSYSTEMS))
    if extra:
        findings.append(f"SUBSYSTEM_AUDIT_UNKNOWN_SUBSYSTEMS:{','.join(extra)}")

    synthesis = payload.get("synthesis")
    if not isinstance(synthesis, dict):
        findings.append("SUBSYSTEM_AUDIT_SYNTHESIS_MISSING")
    else:
        if synthesis.get("audit_status") != "passed":
            findings.append(f"SUBSYSTEM_AUDIT_SYNTHESIS_NOT_PASSED:{synthesis.get('audit_status')}")
        if synthesis.get("tool_exit_code") != 0:
            findings.append(f"SUBSYSTEM_AUDIT_SYNTHESIS_NONZERO_EXIT:{synthesis.get('tool_exit_code')}")
        if not _positive_int(synthesis.get("agent_output_tokens")):
            findings.append("SUBSYSTEM_AUDIT_SYNTHESIS_ZERO_OUTPUT_TOKENS")
        if not _nonempty_list(synthesis.get("evidence_paths")):
            findings.append("SUBSYSTEM_AUDIT_SYNTHESIS_MISSING_EVIDENCE")

    expected_count = len(REQUIRED_SUBSYSTEMS)
    if payload.get("required_subsystem_count") not in {None, expected_count}:
        findings.append(f"SUBSYSTEM_AUDIT_REQUIRED_COUNT_MISMATCH:{payload.get('required_subsystem_count')}:{expected_count}")
    if payload.get("completed_subsystem_count") not in {None, expected_count}:
        findings.append(f"SUBSYSTEM_AUDIT_COMPLETED_COUNT_MISMATCH:{payload.get('completed_subsystem_count')}:{expected_count}")

    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--results", default=str(DEFAULT_RESULTS_PATH))
    args = parser.parse_args()

    findings = verify_results(Path(args.results))
    print(
        json.dumps(
            {
                "success": not findings,
                "required_subsystems": REQUIRED_SUBSYSTEMS,
                "findings": findings,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
