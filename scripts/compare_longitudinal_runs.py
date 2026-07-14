#!/usr/bin/env python3
"""Compare longitudinal runs using the Batch 06 comparison policy."""

from __future__ import annotations

import sys

try:
    from longitudinal_foundation import main as foundation_main
except ModuleNotFoundError:  # pragma: no cover
    from scripts.longitudinal_foundation import main as foundation_main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "compare"]
    raise SystemExit(foundation_main())
