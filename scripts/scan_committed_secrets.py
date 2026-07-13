#!/usr/bin/env python3
"""Fail on committed secret patterns without flagging ordinary fixture IDs."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_PREFIXES = (
    "docs/",
    "reports/",
    "node_modules/",
    "artifacts/",
    ".git/",
)
EXCLUDE_PARTS = ("/tests/",)
EXCLUDE_SUFFIXES = (".md",)

PATTERNS = {
    # OpenAI-style project/user keys are materially longer than common fixture
    # IDs such as task-negative-unsupported.
    "OPENAI_KEY": re.compile(r"\bsk-[A-Za-z0-9_-]{32,}\b"),
    "PRIVATE_KEY": re.compile(r"BEGIN (?:RSA|OPENSSH|EC|DSA)? ?PRIVATE KEY"),
    "JWT_SECRET_DEFAULT": re.compile(r"JWT_SECRET=(?:change-me|[A-Za-z0-9]{16,})"),
    "DEV_API_KEY": re.compile(r"AGENTCO_API_KEY=dev-api-key"),
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    files: list[Path] = []
    for line in out.splitlines():
        if not line:
            continue
        if line.startswith(EXCLUDE_PREFIXES):
            continue
        if any(part in line for part in EXCLUDE_PARTS):
            continue
        if line.endswith(EXCLUDE_SUFFIXES):
            continue
        path = ROOT / line
        if path.is_file():
            files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    findings: list[str] = []
    for path in tracked_files():
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(ROOT)
        for idx, line in enumerate(text.splitlines(), 1):
            for rule, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{rel}:{idx}: {rule}")
    for finding in findings:
        print(finding)
    if findings:
        print("Potential committed secret or production-dangerous default found")
        return 1
    if not args.check:
        print("No committed secret patterns found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
