#!/usr/bin/env python3
"""Offline runnability checks for local Agentco development."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _check(name: str, ok: bool, detail: str) -> bool:
    status = "OK" if ok else "BLOCKED"
    print(f"[{status}] {name}: {detail}")
    return ok


def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def main() -> int:
    print("Agentco doctor: offline deterministic checks")
    checks: list[bool] = []

    checks.append(_check("python", sys.version_info >= (3, 11), sys.version.split()[0]))
    checks.append(_check("node", _command_exists("node"), shutil.which("node") or "install Node.js"))
    checks.append(_check("npm", _command_exists("npm"), shutil.which("npm") or "install npm"))

    backend_pkg = ROOT / "backend" / "package.json"
    frontend_pkg = ROOT / "frontend" / "package.json"
    checks.append(_check("backend package", backend_pkg.exists(), str(backend_pkg)))
    checks.append(_check("frontend package", frontend_pkg.exists(), str(frontend_pkg)))

    for pkg in [backend_pkg, frontend_pkg]:
        if pkg.exists():
            data = json.loads(pkg.read_text())
            checks.append(_check(f"{pkg.parent.name} build script", "build" in data.get("scripts", {}), "npm run build"))

    compose = ROOT / "docker-compose.yml"
    checks.append(_check("compose file", compose.exists(), str(compose)))
    if compose.exists():
        text = compose.read_text()
        for profile in ["minimal", "dev", "full", "demo"]:
            checks.append(_check(f"compose profile {profile}", profile in text, f"--profile {profile}"))

    demo = ROOT / "examples" / "civilization_constitution_demo" / "run_demo.py"
    checks.append(_check("civilization demo", demo.exists(), str(demo)))

    if all(checks):
        print("Doctor passed. Minimal offline targets: make smoke, make demo, make test.")
        return 0

    print("Doctor found blockers. Fix BLOCKED rows before release validation.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
