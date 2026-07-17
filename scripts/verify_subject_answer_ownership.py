#!/usr/bin/env python3
"""Verify subject answer ownership and primitive/capability classification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = ROOT / "artifacts" / "cross-version" / "subject-native-cross-version-v2"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate(campaign_dir: Path = DEFAULT_CAMPAIGN) -> list[str]:
    errors: list[str] = []
    if not campaign_dir.exists():
        return []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = load_json(manifest_path)
    for public_label, subject in manifest.get("subjects", {}).items():
        opaque = subject.get("opaque_label")
        run_path = campaign_dir / "runs" / f"{opaque}.json"
        if not run_path.exists():
            errors.append(f"MISSING_RUN:{public_label}")
            continue
        run = load_json(run_path)
        for item in run.get("case_results", []):
            if item.get("status") != "completed":
                continue
            classification = item.get("operation_classification")
            ownership = item.get("answer_ownership", {})
            case = item.get("case_id")
            if classification == "capability_task":
                if ownership.get("owned_by_subject") is not True:
                    errors.append(f"CAPABILITY_ANSWER_NOT_OWNED_BY_SUBJECT:{public_label}:{case}")
                if len(ownership.get("evidence", [])) < 2:
                    errors.append(f"INSUFFICIENT_ANSWER_OWNERSHIP_EVIDENCE:{public_label}:{case}")
            if item.get("domain") == "calibration" and classification != "runtime_primitive":
                errors.append(f"CALIBRATION_NOT_RUNTIME_PRIMITIVE:{public_label}:{case}")
            if item.get("domain") == "calibration" and classification == "capability_task":
                errors.append(f"CALIBRATION_MISCLASSIFIED_AS_CAPABILITY:{public_label}:{case}")
            if item.get("domain") == "evidence_evaluation" and classification == "capability_task":
                errors.append(f"OBSERVATION_RECORDING_MISCLASSIFIED_AS_EVIDENCE_CAPABILITY:{public_label}:{case}")
            response = item.get("response", {})
            if not response.get("evidence_refs"):
                errors.append(f"COMPLETED_RESPONSE_MISSING_EVIDENCE_REFS:{public_label}:{case}")
            expected_hash = item.get("expected_output_hash")
            if item.get("request_hash") and expected_hash and str(expected_hash) in json.dumps(response):
                errors.append(f"EXPECTED_HASH_LEAKED_TO_RESPONSE:{public_label}:{case}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--campaign-dir", type=Path, default=DEFAULT_CAMPAIGN)
    args = parser.parse_args()
    errors = validate(args.campaign_dir)
    print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
