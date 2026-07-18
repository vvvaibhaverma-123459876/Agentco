#!/usr/bin/env python3
"""Print cross-version comparison summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.campaign_dir / "CONTROL_MANIFEST.json").read_text())
    print(json.dumps(manifest["comparisons"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
