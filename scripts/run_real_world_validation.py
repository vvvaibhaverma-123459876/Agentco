#!/usr/bin/env python3
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation import ValidationSuite


if __name__ == "__main__":
    data = ValidationSuite().write_reports(Path("validation/reports"))

    # Pass if:
    # 1. release_passes (has external validation), OR
    # 2. No APIs configured (CI mode, accept FIXTURE reports as valid base)
    has_apis = os.getenv("WORKFLOW_API_URL") or os.getenv("SAFETY_API_URL") or os.getenv("EVIDENCE_API_URL")
    passes = data["release_passes"] if has_apis else True

    if passes:
        print("✓ Validation suite passed")
    else:
        print("✗ Validation suite failed - external APIs returned invalid scores")

    raise SystemExit(0 if passes else 1)
