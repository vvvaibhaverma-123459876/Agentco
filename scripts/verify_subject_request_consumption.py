#!/usr/bin/env python3
"""Verify that subject-native benchmark results consumed the benchmark request."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAMPAIGN = ROOT / "artifacts" / "cross-version" / "subject-native-cross-version-v1"
FORBIDDEN_TASK_ARGV = {"--help", "--version"}
FORBIDDEN_TASK_COMMAND_FRAGMENT = "verify_mission_progress.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def validate(campaign_dir: Path = DEFAULT_CAMPAIGN) -> list[str]:
    errors: list[str] = []
    if not campaign_dir.exists():
        return []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = load(manifest_path)
    if manifest.get("control_manifest_version") not in {
        "subject-native-cross-version-campaign-v1",
        "real-cross-version-campaign-v1",
    }:
        errors.append("UNKNOWN_CAMPAIGN_VERSION")
    outputs_by_domain: dict[str, set[str]] = {}
    for public_label, subject in manifest.get("subjects", {}).items():
        opaque = subject.get("opaque_label")
        run_path = campaign_dir / "runs" / f"{opaque}.json"
        if not run_path.exists():
            errors.append(f"MISSING_RUN:{public_label}")
            continue
        run = load(run_path)
        for item in run.get("case_results", []):
            status = item.get("status")
            case = item.get("case_id")
            support = item.get("support_status")
            if status == "unsupported" and support == "supported_common":
                errors.append(f"COMMON_CORE_UNSUPPORTED:{public_label}:{case}")
            if status != "completed":
                continue
            request_hash = item.get("request_hash")
            if not request_hash:
                errors.append(f"MISSING_REQUEST_HASH:{public_label}:{case}")
            consumption = item.get("request_consumption", {})
            evidence = consumption.get("evidence", [])
            if consumption.get("consumed") is not True:
                errors.append(f"REQUEST_NOT_CONSUMED:{public_label}:{case}")
            if len(evidence) < 2:
                errors.append(f"INSUFFICIENT_REQUEST_CONSUMPTION_EVIDENCE:{public_label}:{case}")
            process = item.get("process") or {}
            argv = [str(part) for part in process.get("argv", [])]
            if any(part in FORBIDDEN_TASK_ARGV for part in argv):
                errors.append(f"HEALTH_OR_HELP_COMMAND_COUNTED_AS_TASK:{public_label}:{case}")
            if any(FORBIDDEN_TASK_COMMAND_FRAGMENT in part for part in argv):
                errors.append(f"MISSION_PROGRESS_HELP_COUNTED_AS_TASK:{public_label}:{case}")
            measurements = item.get("measurements", [])
            if not any(measurement.get("measurement_scope") == "benchmark_task" for measurement in measurements):
                errors.append(f"MISSING_BENCHMARK_TASK_MEASUREMENT:{public_label}:{case}")
            response_hash = item.get("response_hash")
            if response_hash == request_hash:
                errors.append(f"RESPONSE_HASH_EQUALS_REQUEST_HASH:{public_label}:{case}")
            domain = item.get("domain", "")
            outputs_by_domain.setdefault(domain, set()).add(str(response_hash))
    for domain, outputs in outputs_by_domain.items():
        if domain != "calibration" and len(outputs) == 1:
            errors.append(f"IDENTICAL_OUTPUTS_FOR_DOMAIN:{domain}")
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
