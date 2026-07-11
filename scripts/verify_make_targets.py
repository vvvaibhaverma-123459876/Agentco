#!/usr/bin/env python3
"""Validate that documented Make targets exist.

This is a contract check, not a command executor. It prevents docs from
advertising missing commands while keeping destructive/live targets opt-in.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
JSON_REPORT = REPORT_DIR / "make_target_validation.json"
MD_REPORT = REPORT_DIR / "make_target_validation.md"
DOC_GLOBS = [
    "README.md",
    "docs/**/*.md",
]
MAKE_CMD = re.compile(r"(?:^|[`$]\s*)(?:[A-Z_]+=\\S+\s+)*make\s+([A-Za-z0-9_.:/-]+)")


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def parse_make_targets() -> set[str]:
    targets: set[str] = set()
    for line in MAKEFILE.read_text().splitlines():
        if not line or line.startswith(("\t", " ", ".")) or ":" not in line:
            continue
        name = line.split(":", 1)[0].strip()
        if name and " " not in name and "$" not in name:
            targets.add(name)
    return targets


def docs_to_scan() -> list[Path]:
    paths: set[Path] = set()
    for pattern in DOC_GLOBS:
        paths.update(ROOT.glob(pattern))
    return sorted(path for path in paths if path.is_file())


def discover_advertised_targets() -> list[dict[str, object]]:
    advertised: list[dict[str, object]] = []
    for path in docs_to_scan():
        rel = str(path.relative_to(ROOT))
        for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), start=1):
            for match in MAKE_CMD.finditer(line):
                target = match.group(1).rstrip("`.,)")
                if target == "-C":
                    continue
                advertised.append({"path": rel, "line": line_no, "target": target})
    return advertised


def build_report() -> dict[str, object]:
    targets = parse_make_targets()
    advertised = discover_advertised_targets()
    missing = [item for item in advertised if item["target"] not in targets]
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "commit": run_git(["rev-parse", "HEAD"]),
        "branch": run_git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "working_tree": "dirty" if run_git(["status", "--porcelain"]) else "clean",
        "makefile_target_count": len(targets),
        "advertised_target_count": len(advertised),
        "success": not missing,
        "missing": missing,
    }


def write_report(report: dict[str, object]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    rows = [
        "# Make Target Validation",
        "",
        f"Generated: {report['generated_at']}",
        f"Commit: `{report['commit']}`",
        f"Branch: `{report['branch']}`",
        f"Working tree: `{report['working_tree']}`",
        f"Success: `{report['success']}`",
        "",
        "| Path | Line | Missing target |",
        "|---|---:|---|",
    ]
    missing = report["missing"]
    if missing:
        rows.extend(f"| {item['path']} | {item['line']} | `{item['target']}` |" for item in missing)  # type: ignore[union-attr]
    else:
        rows.append("| none | 0 | none |")
    MD_REPORT.write_text("\n".join(rows) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_report()
    if not args.check:
        write_report(report)
    print(json.dumps({"success": report["success"], "missing": len(report["missing"])}, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
