#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from runtime.controlled_learning.report import build_learning_report, validate_learning_report

REPORT_PATH = ROOT / "docs" / "audit" / "CONTROLLED_LEARNING_REPORT.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without writing")
    args = parser.parse_args()
    report = build_learning_report()
    failures = validate_learning_report(report)
    expected = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        if REPORT_PATH.exists() and REPORT_PATH.read_text() != expected:
            print(f"FAIL: {REPORT_PATH.relative_to(ROOT)} is stale")
            return 1
        print("controlled learning report ok")
        return 0
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(expected)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"wrote {REPORT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
