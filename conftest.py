"""
Root pytest configuration.

Puts both the repository root and the agents/ package directory on sys.path so
tests resolve `runtime.*`, `calibration.*`, `learning.*`, `synthesis.*` (rooted
at the repo) and the V1 `core.*` / `executive.*` packages (rooted at agents/),
regardless of whether pytest is invoked from the repo root or from agents/.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for path in (ROOT, ROOT / "agents"):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)
