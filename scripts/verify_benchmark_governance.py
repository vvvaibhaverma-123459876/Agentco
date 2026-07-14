#!/usr/bin/env python3
"""Validate longitudinal benchmark governance controls."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from longitudinal_foundation import BENCHMARKS, validate_registry
except ModuleNotFoundError:  # pragma: no cover
    from scripts.longitudinal_foundation import BENCHMARKS, validate_registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=BENCHMARKS / "registry.json")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    registry = json.loads(args.registry.read_text())
    errors = validate_registry(registry)
    result = {"success": not errors, "errors": errors}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
