#!/usr/bin/env python3
"""Run a bounded deterministic longitudinal evidence campaign."""

from __future__ import annotations

import argparse

try:
    from longitudinal_foundation import CAMPAIGN_ID, main as foundation_main
except ModuleNotFoundError:  # pragma: no cover
    from scripts.longitudinal_foundation import CAMPAIGN_ID, main as foundation_main


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", default=CAMPAIGN_ID)
    args = parser.parse_args()
    import sys

    sys.argv = [sys.argv[0], "campaign-artifact", "--campaign", args.campaign]
    return foundation_main()


if __name__ == "__main__":
    raise SystemExit(main())
