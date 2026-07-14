#!/usr/bin/env python3
"""Verify real cross-version campaign evidence completeness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_REGISTRY_HASH = "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e"
EXPECTED_EVALUATOR_VERSION = "longitudinal-evaluator-v1"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def validate(campaign_dir: Path, baseline: str, raw: str, reconciled: str) -> list[str]:
    errors: list[str] = []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = load(manifest_path)
    if manifest.get("control_manifest_version") != "real-cross-version-campaign-v1":
        errors.append("SYNTHETIC_OR_UNKNOWN_CAMPAIGN_MANIFEST")
    if manifest.get("methodology") != "subject_process_invocation_no_synthetic_outputs":
        errors.append("METHODOLOGY_NOT_REAL_SUBJECT_INVOCATION")
    if manifest.get("benchmark_registry_hash") != EXPECTED_REGISTRY_HASH:
        errors.append("BENCHMARK_HASH_MISMATCH")
    if manifest.get("evaluator_version") != EXPECTED_EVALUATOR_VERSION:
        errors.append("EVALUATOR_VERSION_MISMATCH")
    if manifest.get("planned_case_executions") != 360:
        errors.append(f"PLANNED_CASE_COUNT_MISMATCH:{manifest.get('planned_case_executions')}")
    blinding = manifest.get("blinding", {})
    if not blinding.get("mapping_hash") or not blinding.get("sealed_mapping"):
        errors.append("MISSING_BLINDING_MAPPING")
    expected = {"version-a": baseline, "version-b": raw, "version-c": reconciled}
    for public_label, sha in expected.items():
        recorded = manifest.get("subjects", {}).get(public_label, {})
        if recorded.get("sha") != sha:
            errors.append(f"SUBJECT_SHA_MISMATCH:{public_label}")
        opaque = recorded.get("opaque_label")
        if not opaque or not str(opaque).startswith("subject-"):
            errors.append(f"SUBJECT_NOT_OPAQUE:{public_label}")
            continue
        run_path = campaign_dir / "runs" / f"{opaque}.json"
        if not run_path.exists():
            errors.append(f"MISSING_SUBJECT_RUN:{public_label}")
            continue
        run = load(run_path)
        if len(run.get("run_ids", [])) != 5:
            errors.append(f"REQUIRED_SEEDS_MISSING:{public_label}")
        cases = run.get("case_results", [])
        if len(cases) != 120:
            errors.append(f"CASE_COUNT_MISMATCH:{public_label}:{len(cases)}")
        for item in cases:
            status = item.get("status")
            if status not in {"completed", "failed", "unsupported", "timeout"}:
                errors.append(f"INVALID_CASE_STATUS:{public_label}:{item.get('case_id')}")
            refs = item.get("runtime_evidence_refs", [])
            if not refs or not all(str(ref).startswith("process://") for ref in refs):
                errors.append(f"UNRESOLVED_RUNTIME_EVIDENCE:{public_label}:{item.get('case_id')}")
            process = item.get("process", {})
            if not process.get("pid") or process.get("wall_clock_ms") is None:
                errors.append(f"MISSING_PROCESS_MEASUREMENT:{public_label}:{item.get('case_id')}")
            if process.get("stdout_hash") is None or process.get("stderr_hash") is None:
                errors.append(f"MISSING_PROCESS_OUTPUT_HASH:{public_label}:{item.get('case_id')}")
            if status == "completed" and item.get("response", {}).get("confidence") is None:
                errors.append(f"COMPLETED_RESPONSE_MISSING_CONFIDENCE:{public_label}:{item.get('case_id')}")
    comparisons = manifest.get("comparisons", {})
    for key in ("a_vs_b", "a_vs_c", "b_vs_c"):
        if key not in comparisons:
            errors.append(f"MISSING_COMPARISON:{key}")
        elif comparisons[key].get("paired_case_count") != 120:
            errors.append(f"PAIRED_COUNT_MISMATCH:{key}")
    if manifest.get("hidden_answer_isolation", {}).get("subject_readable_expected_outputs") is not False:
        errors.append("HIDDEN_ANSWERS_SUBJECT_READABLE")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--raw-candidate", required=True)
    parser.add_argument("--reconciled-candidate", required=True)
    args = parser.parse_args()
    errors = validate(args.campaign_dir, args.baseline, args.raw_candidate, args.reconciled_candidate)
    print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
