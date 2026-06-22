#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validation import ValidationSuite


if __name__ == "__main__":
    data = ValidationSuite().write_reports(Path("validation/reports"))
    raise SystemExit(0 if data["release_passes"] else 1)
