#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
JSON_REPORT = REPORT_DIR / "release_gate_verification.json"
MD_REPORT = REPORT_DIR / "release_gate_verification.md"
LEDGER = ROOT / "BUILD_LEDGER.yaml"


def run_command(command: list[str], timeout: int = 60) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip()
    return {
        "command": " ".join(command),
        "exit_code": proc.returncode,
        "status": "passed" if proc.returncode == 0 else "failed",
        "output_tail": output[-4000:],
    }


def route_reachability() -> dict[str, Any]:
    routes_dir = ROOT / "backend" / "src" / "routes"
    server_text = (ROOT / "backend" / "src" / "server.ts").read_text()
    route_files = sorted(path.name for path in routes_dir.glob("*.routes.ts"))
    route_text = "\n".join((routes_dir / filename).read_text() for filename in route_files)
    missing = []
    registrations = {}
    for filename in route_files:
        module_name = filename.removesuffix(".ts")
        import_pattern = re.compile(
            rf"import\s+\{{(?P<symbols>[^}}]+)\}}\s+from\s+['\"]\./routes/{re.escape(module_name)}['\"]"
        )
        match = import_pattern.search(server_text)
        symbols = []
        if match:
            symbols = [
                symbol.strip().split(" as ")[-1].strip()
                for symbol in match.group("symbols").split(",")
                if symbol.strip()
            ]
        registered = any(f"app.register({symbol}" in server_text for symbol in symbols)
        registrations[filename] = {
            "imported": match is not None,
            "registered": registered,
            "symbols": symbols,
        }
        if match is None or not registered:
            missing.append(filename)
    runtime_endpoints = [
        "/health/runtime",
        "/system/readiness",
        "/system/build-status",
        "/system/feature-gates",
        "/api/civilization/runtime/graph",
        "/api/civilization/runtime/reachability-tick",
        "/api/civilization/runtime/scheduler",
        "/api/civilization/runtime/scheduler/run-once",
    ]
    missing_runtime = [
        endpoint
        for endpoint in runtime_endpoints
        if endpoint not in server_text and endpoint not in route_text
    ]
    passed = not missing and not missing_runtime
    return {
        "scope": "backend_http_route_clusters",
        "status": "partial" if passed else "failed",
        "passed": passed,
        "registered_route_files": route_files,
        "route_registrations": registrations,
        "missing_from_server": missing,
        "required_runtime_endpoints": runtime_endpoints,
        "missing_runtime_endpoints": missing_runtime,
        "honesty_note": (
            "This proves enabled backend route clusters and the core L14 runtime reachability endpoints are registered. "
            "It does not prove full L14 coordinator reachability for every internal service."
        ),
    }


def build_report() -> dict[str, Any]:
    py = sys.executable
    firewall = run_command([py, "-m", "pytest", "calibration/tests/test_ledger_immutability.py::TestFirewall", "-q"])
    sandbox = run_command([py, "selfcoding/tests/test_wall_holds.py"])
    credential = run_command(
        [
            py,
            "-m",
            "pytest",
            "reserve/tests/test_ed25519_signing.py",
            "reserve/tests/test_key_independence_safe.py",
            "-q",
        ]
    )
    reachability = route_reachability()
    gates = {
        "reachability": "partial" if reachability["passed"] else "red",
        "firewall": "green" if firewall["exit_code"] == 0 else "red",
        "sandbox_breach": "green" if sandbox["exit_code"] == 0 else "red",
        "credential_key_independence": "green" if credential["exit_code"] == 0 else "red",
    }
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "success": all(gates[name] == "green" for name in ("firewall", "sandbox_breach", "credential_key_independence")) and reachability["passed"],
        "gates": gates,
        "reachability": reachability,
        "checks": {
            "firewall": firewall,
            "sandbox_breach": sandbox,
            "credential_key_independence": credential,
        },
    }


def update_ledger(report: dict[str, Any]) -> None:
    ledger = yaml.safe_load(LEDGER.read_text())
    ledger.setdefault("gates", {}).update(report["gates"])
    metadata = ledger.setdefault("meta", {})
    metadata["last_updated"] = report["generated_at"]
    metadata["termination_predicate_met"] = (
        ledger.get("rollups", {}).get("verified") == ledger.get("rollups", {}).get("total_items")
        and all(value == "green" for key, value in ledger.get("gates", {}).items() if not key.startswith("_"))
    )
    LEDGER.write_text(yaml.safe_dump(ledger, sort_keys=False, width=120))


def write_reports(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    rows = [
        "# Release Gate Verification",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "| Gate | Status | Evidence |",
        "|---|---|---|",
        f"| reachability | {report['gates']['reachability']} | backend HTTP route registration check; scope is partial, not full L14 graph |",
        f"| firewall | {report['gates']['firewall']} | `{report['checks']['firewall']['command']}` |",
        f"| sandbox_breach | {report['gates']['sandbox_breach']} | `{report['checks']['sandbox_breach']['command']}` |",
        f"| credential_key_independence | {report['gates']['credential_key_independence']} | `{report['checks']['credential_key_independence']['command']}` |",
        "",
        "## Reachability Scope",
        "",
        report["reachability"]["honesty_note"],
        "",
        f"Registered route files: {len(report['reachability']['registered_route_files'])}",
        "",
        "Missing route registrations: " + (", ".join(report["reachability"]["missing_from_server"]) or "none"),
        "",
        "## Result",
        "",
        "The release-blocking safety gates above are based on real commands. Reachability remains `partial` until a full L14 coordinator service graph and runtime trace are implemented.",
    ]
    MD_REPORT.write_text("\n".join(rows) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-ledger", action="store_true")
    args = parser.parse_args()
    report = build_report()
    write_reports(report)
    if args.update_ledger:
        update_ledger(report)
    print(json.dumps({"success": report["success"], "gates": report["gates"], "report": str(JSON_REPORT)}, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
