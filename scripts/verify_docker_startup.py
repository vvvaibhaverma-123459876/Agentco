#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"
REPORT_JSON = REPORT_DIR / "docker_startup_verification.json"
REPORT_MD = REPORT_DIR / "docker_startup_verification.md"
DEFAULT_SERVICES = ["postgres", "redis", "zookeeper", "kafka", "vault", "prometheus", "otel-collector", "grafana"]


def run(command: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout, check=False)
        output = (proc.stdout + proc.stderr).strip()
        return {
            "command": " ".join(command),
            "exit_code": proc.returncode,
            "status": "passed" if proc.returncode == 0 else "failed",
            "output_tail": output[-4000:],
        }
    except Exception as exc:
        return {
            "command": " ".join(command),
            "exit_code": 99,
            "status": "failed",
            "output_tail": f"{exc.__class__.__name__}: {exc}",
        }


def tcp_check(name: str, host: str, port: int, timeout: float = 1.0) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"name": name, "host": host, "port": port, "status": "passed"}
    except Exception as exc:
        return {"name": name, "host": host, "port": port, "status": "failed", "error": f"{exc.__class__.__name__}: {exc}"}


def http_check(name: str, url: str, timeout: float = 2.0) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout) as response:
            return {"name": name, "url": url, "status": "passed", "http_status": response.status}
    except Exception as exc:
        return {"name": name, "url": url, "status": "failed", "error": f"{exc.__class__.__name__}: {exc}"}


def docker_available() -> dict[str, Any]:
    return run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=10)


def wait_for_checks(timeout_seconds: int) -> list[dict[str, Any]]:
    deadline = time.time() + timeout_seconds
    checks: list[dict[str, Any]] = []
    while time.time() < deadline:
        checks = [
            tcp_check("postgres", "localhost", 5432),
            tcp_check("redis", "localhost", 6379),
            tcp_check("kafka", "localhost", 9092),
            tcp_check("vault", "localhost", 8200),
            http_check("prometheus", "http://localhost:9090/-/healthy"),
            http_check("grafana", "http://localhost:3005/api/health"),
            tcp_check("otel_grpc", "localhost", 4317),
            tcp_check("otel_http", "localhost", 4318),
        ]
        if all(check["status"] == "passed" for check in checks):
            return checks
        time.sleep(2)
    return checks


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    config = run(["docker", "compose", "config"], timeout=30)
    info = docker_available()
    if info["exit_code"] != 0:
        return {
            "generated_at": generated_at,
            "success": False,
            "status": "blocked",
            "reason": "docker daemon unavailable",
            "docker_info": info,
            "compose_config": config,
            "services": DEFAULT_SERVICES,
            "checks": [],
        }

    up = run(["docker", "compose", "up", "-d", *DEFAULT_SERVICES], timeout=args.up_timeout)
    ps = run(["docker", "compose", "ps"], timeout=30)
    checks = wait_for_checks(args.health_timeout)
    success = up["exit_code"] == 0 and all(check["status"] == "passed" for check in checks)
    return {
        "generated_at": generated_at,
        "success": success,
        "status": "passed" if success else "failed",
        "docker_info": info,
        "compose_config": config,
        "compose_up": up,
        "compose_ps": ps,
        "services": DEFAULT_SERVICES,
        "checks": checks,
    }


def write_report(report: dict[str, Any]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = [
        "# Docker Startup Verification",
        "",
        f"Generated: {report['generated_at']}",
        "",
        f"Status: `{report['status']}`",
        f"Success: `{report['success']}`",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    if not report["checks"]:
        lines.append(f"| docker_info | {report['docker_info']['status']} | {report['docker_info']['output_tail']} |")
    for check in report["checks"]:
        detail = check.get("url") or f"{check.get('host')}:{check.get('port')}"
        if check.get("error"):
            detail = f"{detail} - {check['error']}"
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    REPORT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--up-timeout", type=int, default=180)
    parser.add_argument("--health-timeout", type=int, default=120)
    args = parser.parse_args()
    report = build_report(args)
    write_report(report)
    print(json.dumps({"success": report["success"], "status": report["status"], "report": str(REPORT_JSON)}, sort_keys=True))
    return 0 if report["success"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
