#!/usr/bin/env python3
"""Validate exact-HEAD runtime execution evidence."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text())
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    errors: list[str] = []
    if ledger.get("commit") != head:
        errors.append(f"ledger commit {ledger.get('commit')} does not match HEAD {head}")
    if ledger.get("final_verdict") != "PASS":
        errors.append(f"ledger final verdict is {ledger.get('final_verdict')}")
    commands = ledger.get("commands", [])
    if not commands:
        errors.append("ledger recorded no commands")
    for item in commands:
        if "exit_code" not in item:
            errors.append(f"command missing exit_code: {item.get('name')}")
        if item.get("exit_code") != 0:
            errors.append(f"command failed: {item.get('name')} exit={item.get('exit_code')}")
    print(json.dumps({"success": not errors, "errors": errors}, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
