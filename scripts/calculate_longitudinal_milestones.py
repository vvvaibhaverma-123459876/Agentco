#!/usr/bin/env python3
"""Calculate longitudinal milestone eligibility from immutable history."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def result(history: dict[str, Any]) -> dict[str, Any]:
    attempts = history.get("attempts", [])
    scheduled_successes = [a for a in attempts if a.get("observation_kind") == "scheduled" and a.get("status") == "success"]
    weeks = sorted({a.get("iso_week") for a in scheduled_successes if a.get("iso_week")})
    commits = sorted({a.get("commit_sha") for a in scheduled_successes if a.get("commit_sha")})
    manual_successes = [a for a in attempts if a.get("observation_kind") == "manual" and a.get("status") == "success"]
    cross_version = len(commits) >= 2 and bool(history.get("benchmark_versions")) and bool(history.get("evaluator_versions"))
    four_week = len(weeks) >= 4 and len(commits) >= 2 and cross_version
    twelve_week = len(weeks) >= 12 and len(commits) >= 3 and not history.get("unresolved_critical_governance_regression", False)
    return {
        "foundation": True,
        "cross_version": cross_version,
        "four_week": four_week,
        "twelve_week": twelve_week,
        "hosted": False,
        "production": False,
        "scheduled_weeks": weeks,
        "scheduled_week_count": len(weeks),
        "scheduled_commit_count": len(commits),
        "manual_success_count": len(manual_successes),
        "manual_runs_advance_calendar": False,
        "time_blocked": [name for name, eligible in {"four_week": four_week, "twelve_week": twelve_week, "hosted": False, "production": False}.items() if not eligible],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.history.read_text())
    calculated = result(data)
    text = json.dumps(calculated, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
