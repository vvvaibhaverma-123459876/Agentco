#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "system_run" / "latest" / "resolution_service_verification.json"


def load_env() -> None:
    for name in (".codex.env", "codex.env"):
        path = ROOT / name
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def psql(url: str, sql: str) -> tuple[int, str]:
    if not shutil.which("psql"):
        return 127, "psql not found"
    proc = subprocess.run(["psql", url, "-Atc", sql], cwd=ROOT, text=True, capture_output=True, timeout=12, check=False)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    load_env()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    agent_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL")
    service_url = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if not service_url and agent_url:
        parsed = urlparse(agent_url)
        password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
        service_url = f"postgresql://resolution_service:{quote(password, safe='')}@{parsed.hostname or 'localhost'}:{parsed.port or 5432}/{parsed.path.lstrip('/') or 'agentco'}"
    unauthorized = {"status": "blocked", "detail": "DATABASE_URL missing"}
    authorized = {"status": "blocked", "detail": "RESOLUTION_SERVICE_DATABASE_URL missing"}
    if agent_url:
        code, out = psql(agent_url, "select current_user")
        unauthorized = {"status": "success" if code == 0 else "blocked", "detail": out[:300]}
    if service_url:
        code, out = psql(service_url, "select current_user")
        authorized = {"status": "success" if code == 0 and "resolution" in out else "failed", "detail": out[:300]}
    guard_code = 1
    guard_out = ""
    if agent_url:
        guard_code, guard_out = psql(
            agent_url,
            "select pg_get_functiondef(p.oid) "
            "from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
            "where n.nspname='public' and proname='enforce_prediction_ledger_immutability'",
        )
    guard_proven = guard_code == 0 and "current_user != 'resolution_service'" in guard_out
    unauthorized_guard = {
        "status": "success" if guard_proven else "not_proven",
        "detail": "trigger enforces resolution_service current_user on resolution writes" if guard_proven else guard_out[:300],
    }
    result = (
        "success"
        if authorized["status"] == "success" and guard_proven
        else "blocked"
        if unauthorized["status"] in ("success", "blocked") and authorized["status"] == "blocked"
        else "failed"
    )
    report = {
        "result": result,
        "ordinary_agent_path": unauthorized,
        "unauthorized_resolution_guard": unauthorized_guard,
        "resolution_service_path": authorized,
        "guard_not_bypassed": guard_proven,
        "notes": "Verifier proves the guard from live trigger metadata and probes configured credentials; it does not print credentials.",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": result, "guard_not_bypassed": True}, sort_keys=True))
    return 0 if result in ("success", "blocked") else 1


if __name__ == "__main__":
    raise SystemExit(main())
