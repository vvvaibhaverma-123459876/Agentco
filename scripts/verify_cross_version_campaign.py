#!/usr/bin/env python3
"""Verify cross-version campaign evidence completeness and subject integrity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_REGISTRY_HASH = "3a1c54f4e54c3f2d7df0b0720dff5112d8179ae4f79fe7f95d2cd0bc2f322d1e"
EXPECTED_EVALUATOR_VERSION = "longitudinal-evaluator-v1"


def validate(campaign_dir: Path, baseline: str, raw: str, reconciled: str) -> list[str]:
    errors: list[str] = []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("benchmark_registry_hash") != EXPECTED_REGISTRY_HASH:
        errors.append("BENCHMARK_HASH_MISMATCH")
    if manifest.get("evaluator_version") != EXPECTED_EVALUATOR_VERSION:
        errors.append("EVALUATOR_VERSION_MISMATCH")
    expected = {"version-a": baseline, "version-b": raw, "version-c": reconciled}
    for subject, sha in expected.items():
        recorded = manifest.get("subjects", {}).get(subject, {})
        if recorded.get("sha") != sha:
            errors.append(f"SUBJECT_SHA_MISMATCH:{subject}")
        run_path = campaign_dir / "runs" / f"{subject}.json"
        if not run_path.exists():
            errors.append(f"MISSING_SUBJECT_RUN:{subject}")
            continue
        run = json.loads(run_path.read_text())
        if len(run.get("run_ids", [])) != 5:
            errors.append(f"REQUIRED_SEEDS_MISSING:{subject}")
        cases = run.get("case_results", [])
        if len(cases) != 120:
            errors.append(f"CASE_COUNT_MISMATCH:{subject}:{len(cases)}")
        for item in cases:
            if item.get("status") not in {"passed", "failed", "unsupported", "timeout"}:
                errors.append(f"INVALID_CASE_STATUS:{subject}:{item.get('case_id')}")
            if item.get("output", {}).get("confidence") is None:
                errors.append(f"MISSING_CONFIDENCE:{subject}:{item.get('case_id')}")
            if item.get("output", {}).get("budget_use") is None:
                errors.append(f"MISSING_RESOURCE_USAGE:{subject}:{item.get('case_id')}")
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
