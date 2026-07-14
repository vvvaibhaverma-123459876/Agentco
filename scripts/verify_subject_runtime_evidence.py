#!/usr/bin/env python3
"""Resolve runtime-origin evidence references from real cross-version campaigns."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate(campaign_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = campaign_dir / "CONTROL_MANIFEST.json"
    if not manifest_path.exists():
        return ["MISSING_CONTROL_MANIFEST"]
    manifest = json.loads(manifest_path.read_text())
    for public_label, subject in manifest.get("subjects", {}).items():
        opaque = subject.get("opaque_label")
        run_path = campaign_dir / "runs" / f"{opaque}.json"
        if not run_path.exists():
            errors.append(f"MISSING_RUN:{public_label}")
            continue
        run = json.loads(run_path.read_text())
        for item in run.get("case_results", []):
            for ref in item.get("runtime_evidence_refs", []):
                if not str(ref).startswith(f"process://{opaque}/"):
                    errors.append(f"UNRESOLVABLE_REF:{public_label}:{item.get('case_id')}:{ref}")
            process = item.get("process", {})
            if process.get("pid") is None or process.get("stdout_hash") is None or process.get("wall_clock_ms") is None:
                errors.append(f"MISSING_PROCESS_EVIDENCE:{public_label}:{item.get('case_id')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.campaign_dir)
    print(json.dumps({"success": not errors, "errors": errors}, indent=2, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
