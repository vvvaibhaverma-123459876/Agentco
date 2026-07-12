#!/usr/bin/env python3
"""Fail closed on active gate and verification bypass patterns."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
JSON_REPORT = REPORT_DIR / "gate_integrity.json"
MD_REPORT = REPORT_DIR / "gate_integrity.md"
DEFAULT_EXCEPTIONS = ROOT / "docs" / "audit" / "current" / "GATE_INTEGRITY_EXCEPTIONS.json"

PROTECTED_GLOBS = [
    "Makefile",
    ".github/workflows/**/*.yml",
    ".github/workflows/**/*.yaml",
    "package.json",
    "backend/package.json",
    "frontend/package.json",
    "scripts/**/*.py",
    "scripts/**/*.sh",
    "docker-compose*.yml",
    "Dockerfile*",
    "backend/Dockerfile*",
    "frontend/Dockerfile*",
    "pytest.ini",
    "pyproject.toml",
    "jest.config.*",
    "backend/jest.config.*",
    "frontend/jest.config.*",
]

EXCLUDED_PREFIXES = (
    "archive/",
    "docs/history/",
    "docs/archive/",
    "reports/",
    "artifacts/",
    "node_modules/",
    "backend/node_modules/",
    "frontend/node_modules/",
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    detail: str


@dataclass(frozen=True)
class GateException:
    rule: str
    path: str
    line: int | None
    match: str | None
    justification: str
    owner: str
    expiry_date: str
    risk: str


RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("MASKED_FAILURE", re.compile(r"\|\|\s*true"), "Command masks a non-zero exit status with `|| true`."),
    (
        "MASKED_SUCCESS_OUTPUT",
        re.compile(r"\|\|\s*echo\s+.*(pass|success|ready|verified|complete)", re.IGNORECASE),
        "Command can convert a failure into success-like output.",
    ),
    ("CONTINUE_ON_ERROR", re.compile(r"continue-on-error:\s*true"), "Workflow step allows failure to continue."),
    ("SET_PLUS_E", re.compile(r"(^|[;&|]\s*)set\s+\+e\b"), "Verification shell disables fail-fast behavior."),
    ("FORCE_EXIT", re.compile(r"--forceExit\b"), "Jest force-exit escape hatch is not allowed in active gates."),
    ("PASS_WITH_NO_TESTS", re.compile(r"passWithNoTests"), "Test command can pass with no tests."),
    (
        "PYTEST_ZERO_TESTS",
        re.compile(r"(?:^|\s)(?:\$\([A-Z_]+\)|python\S*|python|\$\(PYTHON\))?\s*(?:-m\s+)?pytest\b(?!.*--collect-only)(?!.*(?:verify_pytest_skips|--strict-zero-tests))"),
        "Raw pytest command is not governed against zero-test execution in protected gate surfaces.",
    ),
    (
        "SUBPROCESS_CHECK_FALSE",
        re.compile(r"subprocess\.(?:run|call|Popen)\([^\\n]*check\s*=\s*False"),
        "Protected verification path uses subprocess without fail-closed status handling.",
    ),
    ("OS_SYSTEM", re.compile(r"\bos\.system\("), "Protected verification path uses os.system without structured exit handling."),
    ("SILENT_EXCEPT", re.compile(r"except\s+[^:\n]*:\s*(?:#.*)?$"), "Broad one-line exception handler may silently suppress errors."),
    ("SILENT_CATCH", re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "Empty catch block suppresses verification errors."),
    ("UNCONDITIONAL_EXIT_ZERO", re.compile(r"\bexit\s+0\b|sys\.exit\(0\)|process\.exit\(0\)"), "Protected gate exits success unconditionally."),
    (
        "PRODUCTION_READY_OUTPUT",
        re.compile(r"ALL GATES PASSED|READY FOR PRODUCTION|PRODUCTION_READY", re.IGNORECASE),
        "Active gate prints production-readiness language.",
    ),
    (
        "SIMULATED_VERIFICATION",
        re.compile(r"would verify|would test|expected in CI", re.IGNORECASE),
        "Active gate describes verification instead of executing it.",
    ),
]


def run_git(root: Path, args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def iter_candidate_files(root: Path) -> list[Path]:
    paths: set[Path] = set()
    tracked = run_git(root, ["ls-files"]).splitlines()
    for raw in tracked:
        rel = raw.replace("\\", "/")
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        for pattern in PROTECTED_GLOBS:
            if fnmatch.fnmatch(rel, pattern):
                paths.add(root / rel)
                break
    return sorted(paths)


def load_exceptions(path: Path) -> list[GateException]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    entries = raw.get("exceptions", raw if isinstance(raw, list) else [])
    result: list[GateException] = []
    for item in entries:
        result.append(
            GateException(
                rule=str(item["rule"]),
                path=str(item["file"]),
                line=int(item["line"]) if item.get("line") is not None else None,
                match=str(item["match"]) if item.get("match") is not None else None,
                justification=str(item["justification"]),
                owner=str(item["owner"]),
                expiry_date=str(item["expiry_date"]),
                risk=str(item["risk"]),
            )
        )
    return result


def exception_matches(exc: GateException, finding: Finding, line_text: str) -> bool:
    if exc.rule != finding.rule or exc.path != finding.path:
        return False
    if exc.line is not None and exc.line != finding.line:
        return False
    if exc.match is not None and exc.match not in line_text:
        return False
    return True


def is_expired(expiry: str) -> bool:
    return date.fromisoformat(expiry) < date.today()


def make_targets(root: Path) -> dict[str, list[tuple[int, str]]]:
    makefile = root / "Makefile"
    lines = makefile.read_text().splitlines()
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


def scan_text_patterns(root: Path, exceptions: list[GateException]) -> tuple[list[Finding], list[GateException]]:
    findings: list[Finding] = []
    matched_exceptions: set[int] = set()
    for path in iter_candidate_files(root):
        rel = str(path.relative_to(root))
        try:
            lines = path.read_text(errors="replace").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            for rule, pattern, detail in RULES:
                if not pattern.search(line):
                    continue
                finding = Finding(rel, index, rule, detail)
                matched = False
                for exc_index, exc in enumerate(exceptions):
                    if exception_matches(exc, finding, line):
                        matched_exceptions.add(exc_index)
                        matched = True
                        break
                if not matched:
                    findings.append(finding)
    stale = [exc for idx, exc in enumerate(exceptions) if idx not in matched_exceptions]
    for exc in exceptions:
        if is_expired(exc.expiry_date):
            findings.append(Finding(exc.path, exc.line or 0, "EXPIRED_EXCEPTION", f"Gate exception expired on {exc.expiry_date}."))
    for exc in stale:
        findings.append(Finding(exc.path, exc.line or 0, "STALE_EXCEPTION", "Gate exception matched no protected finding."))
    return findings, stale


def scan_target_contracts(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    targets = make_targets(root)
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
        findings.append(Finding("Makefile", 0, "MISSING_TARGET", f"Required target `{target}` is not defined."))

    for target in ("autonomy-learner-test", "autonomy-simulator-test"):
        body = "\n".join(line for _, line in targets.get(target, []))
        if "python" in body.lower() and "-c" in body and "print(" in body:
            line_no = targets[target][0][0] if targets.get(target) else 0
            findings.append(Finding("Makefile", line_no, "PRINT_ONLY_TARGET", f"`{target}` uses a print-only command."))
        if "npm test" not in body and "pytest" not in body:
            line_no = targets[target][0][0] if targets.get(target) else 0
            findings.append(Finding("Makefile", line_no, "WEAK_TARGET", f"`{target}` does not execute a real test runner."))

    prod_body = "\n".join(line for _, line in targets.get("production-release-gate", []))
    if prod_body:
        if "exit 2" not in prod_body:
            line_no = targets["production-release-gate"][0][0]
            findings.append(Finding("Makefile", line_no, "ALTERNATE_GATE_ACTIVE", "`production-release-gate` must fail closed."))
        if "make release-gate" not in prod_body and "$(MAKE) release-gate" not in prod_body:
            line_no = targets["production-release-gate"][0][0]
            findings.append(Finding("Makefile", line_no, "ALTERNATE_GATE_MISSING_POINTER", "`production-release-gate` must point to `make release-gate`."))

    release_body = "\n".join(line for _, line in targets.get("release-gate", []))
    if "$(MAKE) gate-integrity" not in release_body and "make gate-integrity" not in release_body:
        findings.append(Finding("Makefile", 0, "RELEASE_GATE_MISSING_INTEGRITY", "`release-gate` must run `gate-integrity`."))
    return findings


def build_report(root: Path, exceptions_path: Path) -> dict[str, object]:
    commit = run_git(root, ["rev-parse", "HEAD"])
    branch = run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    dirty = bool(run_git(root, ["status", "--porcelain"]))
    exceptions = load_exceptions(exceptions_path)
    text_findings, _ = scan_text_patterns(root, exceptions)
    findings = text_findings + scan_target_contracts(root)
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "commit": commit,
        "branch": branch,
        "working_tree": "dirty" if dirty else "clean",
        "success": not findings,
        "protected_files": [str(path.relative_to(root)) for path in iter_candidate_files(root)],
        "exception_file": str(exceptions_path.relative_to(root)) if exceptions_path.is_relative_to(root) else str(exceptions_path),
        "exception_count": len(exceptions),
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    args = parser.parse_args()
    report = build_report(args.root.resolve(), args.exceptions.resolve())
    if not args.check:
        write_report(report)
    print(json.dumps({"success": report["success"], "findings": len(report["findings"])}, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
