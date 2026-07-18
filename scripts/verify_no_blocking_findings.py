#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FINDINGS_DIR = ROOT / "docs" / "audit" / "current"
BLOCKING_STATUSES = {"open_blocking", "open_hold_for_more_evidence"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def iter_findings(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        findings = value.get("findings")
        if isinstance(findings, list):
            return [item for item in findings if isinstance(item, dict)]
    return []


def scan_findings(findings_dir: Path) -> list[dict[str, Any]]:
    open_items: list[dict[str, Any]] = []
    for path in sorted(findings_dir.glob("*.json")):
        try:
            payload = load_json(path)
        except json.JSONDecodeError as exc:
            open_items.append(
                {
                    "path": str(path),
                    "finding_id": "INVALID_FINDINGS_JSON",
                    "status": "open_blocking",
                    "severity": "S0",
                    "summary": f"Findings file is not valid JSON: {exc.msg}",
                }
            )
            continue
        for finding in iter_findings(payload):
            status = finding.get("status")
            if status in BLOCKING_STATUSES:
                open_items.append(
                    {
                        "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path),
                        "finding_id": finding.get("finding_id", "UNKNOWN_FINDING"),
                        "status": status,
                        "severity": finding.get("severity", "UNKNOWN"),
                        "summary": finding.get("summary", ""),
                    }
                )
    return open_items


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--findings-dir", default=str(DEFAULT_FINDINGS_DIR))
    args = parser.parse_args()

    open_items = scan_findings(Path(args.findings_dir))
    print(json.dumps({"success": not open_items, "open_findings": open_items}, indent=2, sort_keys=True))
    return 1 if open_items else 0


if __name__ == "__main__":
    raise SystemExit(main())
