#!/usr/bin/env python3
"""Verify production deployment posture without printing secrets."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


REPORT_DIR = Path("reports/system_run/latest")
REPORT_PATH = REPORT_DIR / "production_posture_verification.json"

REQUIRED_SECRET_VARS = [
    "AGENTCO_API_KEY",
    "JWT_SECRET",
    "EVENT_BUS_SIGNING_KEY",
    "EVENT_BUS_HMAC_KEY",
    "DATABASE_URL",
    "VAULT_ADDR",
    "VAULT_TOKEN",
    "SPECIALIST_SHARED_SECRET",
]

DANGEROUS_VALUES = {
    "dev-api-key",
    "dev-key-replace-in-production",
    "dev-insecure-key",
    "change-me-generate-with-openssl-rand-hex-64",
    "root",
    "default-insecure-secret",
    "development-only-specialist-secret",
}


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []

    for name in REQUIRED_SECRET_VARS:
        value = os.getenv(name)
        if not value:
            checks.append(check(name, "blocked", "missing required production secret"))
        elif value in DANGEROUS_VALUES or "password@localhost" in value:
            checks.append(check(name, "blocked", "dev/default value is not allowed"))
        else:
            checks.append(check(name, "real", "present; value suppressed"))

    checks.extend(check_tcp_services())
    checks.append(check_docker_compose())

    blocked = [c for c in checks if c["status"] in {"blocked", "broken", "missing"}]
    report = {
        "mode": "production_posture",
        "can_continue": not blocked,
        "checks": checks,
        "blocked": blocked,
        "required_fixes": [f"{c['name']}: {c['detail']}" for c in blocked],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(REPORT_PATH), "can_continue": report["can_continue"], "blocked_count": len(blocked)}))
    return 0 if report["can_continue"] else 2


def check(name: str, status: str, detail: str) -> dict[str, str]:
    return {"name": name, "status": status, "detail": detail}


def check_tcp_services() -> list[dict[str, str]]:
    services = [
        ("postgres", os.getenv("POSTGRES_HOST", "localhost"), int(os.getenv("POSTGRES_PORT", "5432"))),
        ("redis", os.getenv("REDIS_HOST", "localhost"), int(os.getenv("REDIS_PORT", "6379"))),
        ("kafka", os.getenv("KAFKA_HOST", "localhost"), int(os.getenv("KAFKA_PORT", "9092"))),
        ("vault", os.getenv("VAULT_HOST", "localhost"), int(os.getenv("VAULT_PORT", "8200"))),
        ("prometheus", os.getenv("PROMETHEUS_HOST", "localhost"), int(os.getenv("PROMETHEUS_PORT", "9090"))),
        ("grafana", os.getenv("GRAFANA_HOST", "localhost"), int(os.getenv("GRAFANA_PORT", "3005"))),
    ]
    return [tcp_check(name, host, port) for name, host, port in services]


def tcp_check(name: str, host: str, port: int) -> dict[str, str]:
    try:
        with socket.create_connection((host, port), timeout=1.5):
            return check(name, "real", f"tcp reachable at {host}:{port}")
    except OSError as exc:
        return check(name, "blocked", f"tcp unavailable at {host}:{port}: {exc.__class__.__name__}")


def check_docker_compose() -> dict[str, str]:
    docker = shutil.which("docker")
    if not docker:
        return check("docker_compose", "blocked", "docker CLI missing")
    try:
        result = subprocess.run(
            [docker, "compose", "ps", "--format", "json"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            timeout=10,
        )
    except Exception as exc:
        return check("docker_compose", "blocked", f"docker compose probe failed: {exc.__class__.__name__}")
    if result.returncode != 0:
        return check("docker_compose", "blocked", "docker compose is unavailable or project is not running")
    return check("docker_compose", "real", "docker compose responded")


if __name__ == "__main__":
    sys.exit(main())
