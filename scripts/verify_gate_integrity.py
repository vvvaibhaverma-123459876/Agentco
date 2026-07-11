#!/usr/bin/env python3
"""Fail closed on active release-gate bypass patterns.

This checker is intentionally narrow: it scans active release commands and
their verification scripts, not archived reports or historical docs. Historical
claims can remain for audit provenance, but active gates must not mask failures
or print production readiness without executable evidence.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKEFILE = ROOT / "Makefile"
PROTECTED_FILES = [
    MAKEFILE,
    ROOT / "scripts" / "verify_release_gates.py",
]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
JSON_REPORT = REPORT_DIR / "gate_integrity.json"
MD_REPORT = REPORT_DIR / "gate_integrity.md"


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    detail: str


def run_git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def make_targets() -> dict[str, list[tuple[int, str]]]:
    lines = MAKEFILE.read_text().splitlines()
    targets: dict[str, list[tuple[int, str]]] = {}
    current: str | None = None
    for index, line in enumerate(lines, start=1):
        if line and not line.startswith(("\t", " ")) and ":" in line and not line.startswith("."):
            name = line.split(":", 1)[0].strip()
            if name and " " not in name and "$" not in name:
                current = name
                targets.setdefault(current, [])
            else:
                current = None
            continue
        if current and line.startswith("\t"):
            targets[current].append((index, line))
        elif line and not line.startswith(("\t", " ")):
            current = None
    return targets


def scan_text_patterns() -> list[Finding]:
    findings: list[Finding] = []
    patterns = [
        (
            "masked_failure",
            re.compile(r"\|\|\s*true"),
            "Command masks a non-zero exit status with `|| true`.",
        ),
        (
            "force_exit",
            re.compile(r"--forceExit|passWithNoTests"),
            "Jest force-exit/pass-with-no-tests escape hatch is not allowed in active gates.",
        ),
        (
            "production_ready_claim",
            re.compile(r"ALL GATES PASSED|READY FOR PRODUCTION|PRODUCTION_READY"),
            "Active gate prints production-readiness language.",
        ),
        (
            "expected_ci_failure",
            re.compile(r"expected in CI|would verify|would test"),
            "Active gate describes a failure or test as expected instead of executing it.",
        ),
    ]
    allowed_masked_fragments = {
        'pkill -f "run_level3_functional_verification.sh" || true',
    }
    for path in PROTECTED_FILES:
        if not path.exists():
            findings.append(Finding(str(path.relative_to(ROOT)), 0, "missing_file", "Protected gate file is missing."))
            continue
        for index, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            for rule, pattern, detail in patterns:
                if not pattern.search(line):
                    continue
                if rule == "masked_failure" and any(fragment in line for fragment in allowed_masked_fragments):
                    continue
                findings.append(Finding(str(path.relative_to(ROOT)), index, rule, detail))
    return findings


def scan_target_contracts() -> list[Finding]:
    findings: list[Finding] = []
    targets = make_targets()

    required = {
        "release-gate",
        "gate-integrity",
        "verify-advertised-targets",
        "verify-clean-room",
        "audit-clean-room",
        "autonomy-learner-test",
        "autonomy-simulator-test",
    }
    for target in sorted(required - targets.keys()):
        findings.append(Finding("Makefile", 0, "missing_target", f"Required target `{target}` is not defined."))

    for target in ("autonomy-learner-test", "autonomy-simulator-test"):
        body = "\n".join(line for _, line in targets.get(target, []))
        if "python" in body.lower() and "-c" in body and "print(" in body:
            line_no = targets[target][0][0] if targets.get(target) else 0
            findings.append(Finding("Makefile", line_no, "print_only_target", f"`{target}` uses a print-only command."))
        if "npm test" not in body and "pytest" not in body:
            line_no = targets[target][0][0] if targets.get(target) else 0
            findings.append(Finding("Makefile", line_no, "weak_target", f"`{target}` does not execute a real test runner."))

    prod_body = "\n".join(line for _, line in targets.get("production-release-gate", []))
    if prod_body:
        if "exit 2" not in prod_body:
            line_no = targets["production-release-gate"][0][0]
            findings.append(Finding("Makefile", line_no, "alternate_gate_active", "`production-release-gate` must fail closed."))
        if "make release-gate" not in prod_body and "$(MAKE) release-gate" not in prod_body:
            line_no = targets["production-release-gate"][0][0]
            findings.append(Finding("Makefile", line_no, "alternate_gate_missing_pointer", "`production-release-gate` must point to `make release-gate`."))

    release_body = "\n".join(line for _, line in targets.get("release-gate", []))
    if "$(MAKE) gate-integrity" not in release_body and "make gate-integrity" not in release_body:
        findings.append(Finding("Makefile", 0, "release_gate_missing_integrity", "`release-gate` must run `gate-integrity`."))

    return findings


def build_report() -> dict[str, object]:
    commit = run_git(["rev-parse", "HEAD"])
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    dirty = bool(run_git(["status", "--porcelain"]))
    findings = scan_text_patterns() + scan_target_contracts()
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "commit": commit,
        "branch": branch,
        "working_tree": "dirty" if dirty else "clean",
        "success": not findings,
        "protected_files": [str(path.relative_to(ROOT)) for path in PROTECTED_FILES],
        "findings": [asdict(finding) for finding in findings],
    }


def write_report(report: dict[str, object]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    findings = report["findings"]
    rows = [
        "# Gate Integrity",
        "",
        f"Generated: {report['generated_at']}",
        f"Commit: `{report['commit']}`",
        f"Branch: `{report['branch']}`",
        f"Working tree: `{report['working_tree']}`",
        f"Success: `{report['success']}`",
        "",
        "| Path | Line | Rule | Detail |",
        "|---|---:|---|---|",
    ]
    if findings:
        rows.extend(
            f"| {item['path']} | {item['line']} | {item['rule']} | {item['detail']} |"
            for item in findings  # type: ignore[union-attr]
        )
    else:
        rows.append("| none | 0 | none | No active gate-integrity findings. |")
    MD_REPORT.write_text("\n".join(rows) + "\n")


def main() -> int:
    check_only = "--check" in sys.argv
    report = build_report()
    if not check_only:
        write_report(report)
    print(json.dumps({"success": report["success"], "findings": len(report["findings"])}, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
