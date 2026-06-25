"""AgentCo runtime doctor.

Produces a precise capability report without hiding degraded behavior.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .modes import RUNTIME_MODES, choose_runtime_mode, classify_mode


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"


@dataclass
class Check:
    service: str
    status: str
    detail: str
    remediation: str = ""

    def to_dict(self) -> dict:
        return {
            "service": self.service,
            "status": self.status,
            "detail": self.detail,
            "remediation": self.remediation,
        }


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run_cmd(cmd: list[str], cwd: Path = ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, f"{' '.join(cmd)} timed out after {timeout}s"


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def check_port(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_python() -> Check:
    ok = sys.version_info >= (3, 11)
    return Check("python", "real" if ok else "broken", sys.version.split()[0], "Use Python 3.13 for AgentCo doctor/tests")


def check_python_dependencies() -> Check:
    missing = [name for name in ("pytest",) if importlib.util.find_spec(name) is None]
    if missing:
        return Check("python_dependencies", "broken", f"missing {', '.join(missing)}", "Install runtime test deps or use python3.13")
    return Check("python_dependencies", "real", "pytest importable")


def check_binary(service: str, binary: str) -> Check:
    path = shutil.which(binary)
    return Check(service, "real" if path else "missing", path or f"{binary} not found", f"Install {binary}")


def check_docker_daemon() -> Check:
    if not command_exists("docker"):
        return Check("docker_daemon", "missing", "docker CLI missing", "Install Docker")
    code, out = run_cmd(["docker", "ps"], timeout=8)
    if code == 0:
        return Check("docker_daemon", "real", "docker daemon reachable")
    return Check("docker_daemon", "blocked", out[:300], "Start Docker Desktop/daemon or use local_native")


def check_docker_compose() -> Check:
    if not command_exists("docker"):
        return Check("docker_compose", "missing", "docker CLI missing", "Install Docker")
    code, out = run_cmd(["docker", "compose", "version"], timeout=8)
    if code == 0:
        return Check("docker_compose", "real", out)
    return Check("docker_compose", "missing", out[:300], "Install Docker Compose plugin or use local_native")


def check_postgres() -> Check:
    db_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or "postgresql://agentco:password@localhost:5432/agentco"
    code, out = run_cmd(["psql", db_url, "-Atc", "select current_database(), current_user"], timeout=8)
    if code == 0:
        return Check("postgres", "real", out)
    return Check("postgres", "missing", out[:300] or "psql failed", "Start native Postgres or use offline_fixture")


def check_migrations() -> Check:
    if not (ROOT / "backend" / "src" / "db" / "migrate.ts").exists():
        return Check("migrations", "missing", "backend TypeScript migration runner missing")
    return Check("migrations", "real", "backend TypeScript migration runner present")


def check_migration_dependencies() -> Check:
    pkg = ROOT / "backend" / "package.json"
    if not pkg.exists():
        return Check("migration_dependencies", "missing", "backend/package.json missing")
    data = json.loads(pkg.read_text())
    deps = data.get("dependencies", {})
    if "pg" not in deps:
        return Check("migration_dependencies", "broken", "pg dependency missing", "Install backend Node dependencies")
    code, out = run_cmd(["npx", "ts-node", "--version"], cwd=ROOT / "backend", timeout=12)
    if code == 0:
        return Check("migration_dependencies", "real", f"pg dependency declared; ts-node runnable ({out})")
    return Check("migration_dependencies", "broken", out[:300], "Install backend Node dependencies so npx ts-node works")


def check_core_schema() -> Check:
    db_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or "postgresql://agentco:password@localhost:5432/agentco"
    sql = "select to_regclass('public.prediction_ledger'), to_regclass('public.decision_log'), to_regclass('public.event_history'), to_regclass('public.trust_scores')"
    code, out = run_cmd(["psql", db_url, "-Atc", sql], timeout=8)
    if code == 0 and "prediction_ledger" in out and "decision_log" in out and "event_history" in out and "trust_scores" in out:
        return Check("core_db_schema", "real", out)
    return Check("core_db_schema", "broken", out[:300], "Run npm run db:migrate with a reachable Postgres")


def check_tcp_service(service: str, host: str, port: int, remediation: str) -> Check:
    if check_port(host, port):
        return Check(service, "real", f"{host}:{port} reachable")
    return Check(service, "missing", f"{host}:{port} unreachable", remediation)


def check_openai_env() -> Check:
    key_present = bool(os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))
    model = os.getenv("LLM_MODEL_DEFAULT", "unset")
    return Check("openai_env", "real" if key_present else "missing", f"key_present={key_present}, model={model}", "Set LLM_API_KEY or use offline_fixture")


def check_openai_connectivity(live: bool) -> Check:
    if not live:
        return Check("openai_connectivity", "not_required", "live OpenAI check not requested")
    script = ROOT / "scripts" / "verify_openai_connectivity.py"
    if not script.exists():
        return Check("openai_connectivity", "missing", "connectivity script missing")
    code, out = run_cmd([sys.executable, str(script)], timeout=45)
    if code == 0:
        return Check("openai_connectivity", "real", "OpenAI-compatible call succeeded")
    return Check("openai_connectivity", "broken", out[-500:], "Check LLM_API_KEY/LLM_BASE_URL or use offline_fixture")


def check_resolution_service() -> Check:
    db_url = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if not db_url:
        base = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL")
        password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
        if base:
            from urllib.parse import quote, urlparse
            parsed = urlparse(base)
            db_url = f"postgresql://resolution_service:{quote(password, safe='')}@{parsed.hostname or 'localhost'}:{parsed.port or 5432}/{parsed.path.lstrip('/') or 'agentco'}"
    if not db_url:
        return Check("resolution_service", "missing", "no DATABASE_URL/RESOLUTION_SERVICE_DATABASE_URL", "Set RESOLUTION_SERVICE_DATABASE_URL for ledger scoring")
    code, out = run_cmd(["psql", db_url, "-Atc", "select current_user"], timeout=8)
    if code == 0 and "resolution_service" in out:
        return Check("resolution_service", "real", "resolution_service login works")
    return Check("resolution_service", "blocked", out[:300], "Run migration 016 and set RESOLUTION_SERVICE_PASSWORD/URL")


def check_filesystem_reports() -> Check:
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        probe = REPORT_DIR / ".doctor_write_probe"
        probe.write_text("ok\n")
        probe.unlink()
        return Check("filesystem_reports", "real", str(REPORT_DIR))
    except OSError as exc:
        return Check("filesystem_reports", "broken", str(exc), "Fix filesystem permissions")


def check_backend_health() -> Check:
    try:
        with urllib.request.urlopen("http://localhost:3101/health", timeout=2) as response:
            return Check("backend_health", "real", f"status={response.status}")
    except (urllib.error.URLError, TimeoutError):
        return Check("backend_health", "not_required", "backend not running during doctor")


def check_sensitive_route_auth() -> Check:
    try:
        with urllib.request.urlopen("http://localhost:3101/api/overrides", timeout=2) as response:
            return Check("sensitive_route_auth", "broken", f"unexpected status={response.status}", "Protect sensitive routes with requireScope")
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return Check("sensitive_route_auth", "real", f"/api/overrides unauthenticated status={exc.code}")
        return Check("sensitive_route_auth", "broken", f"unexpected HTTP {exc.code}")
    except (urllib.error.URLError, TimeoutError):
        # Static source check keeps the doctor useful without a running backend.
        route = ROOT / "backend" / "src" / "routes" / "override.routes.ts"
        text = route.read_text() if route.exists() else ""
        if "fastify.get('/api/overrides', { preHandler: requireScope('governance:mutate')" in text:
            return Check("sensitive_route_auth", "real", "static route check passed")
        return Check("sensitive_route_auth", "broken", "backend not running and static route check failed")


def check_build(service: str, command: list[str], cwd: Path, run_builds: bool) -> Check:
    if not run_builds:
        pkg = cwd / "package.json"
        if pkg.exists() and '"build"' in pkg.read_text():
            return Check(service, "not_required", "build command not run in this mode")
        return Check(service, "missing", "package/build script missing")
    code, out = run_cmd(command, cwd=cwd, timeout=90)
    return Check(service, "real" if code == 0 else "broken", out[-500:] or "ok", f"Run {' '.join(command)}")


def collect_checks(mode: str, live_openai: bool = False, run_builds: bool = False) -> list[Check]:
    load_env_file(ROOT / ".codex.env")
    checks = [
        check_python(),
        check_python_dependencies(),
        check_binary("node", "node"),
        check_binary("npm", "npm"),
        check_build("backend_build", ["npm", "run", "build"], ROOT / "backend", run_builds),
        check_build("frontend_build", ["npm", "run", "build"], ROOT / "frontend", run_builds),
        check_binary("docker_cli", "docker"),
        check_docker_daemon(),
        check_docker_compose(),
        check_postgres(),
        check_migration_dependencies(),
        check_migrations(),
        check_core_schema(),
        check_tcp_service("redis", "localhost", 6379, "Start Redis or use memory cache fallback"),
        check_tcp_service("kafka", "localhost", 9092, "Start Kafka or use in-process event bus fallback"),
        check_tcp_service("vault", "localhost", 8200, "Start Vault or use env secret provider fallback"),
        check_tcp_service("prometheus", "localhost", 9090, "Start Prometheus or use JSON metrics fallback"),
        check_tcp_service("grafana", "localhost", 3005, "Start Grafana or skip dashboard UI"),
        check_openai_env(),
        check_openai_connectivity(live_openai),
        check_resolution_service(),
        check_backend_health(),
        check_sensitive_route_auth(),
        check_filesystem_reports(),
    ]
    if mode in ("offline_fixture", "ci_smoke"):
        for check in checks:
            if check.service in {"postgres", "core_db_schema", "resolution_service"} and check.status != "real":
                check.status = "not_required"
    return checks


def build_report(requested_mode: str, checks: list[Check]) -> dict:
    service_status = {check.service: check.status for check in checks}
    selected = choose_runtime_mode(requested_mode, service_status)
    classification = classify_mode(selected, service_status)
    required_fixes = [
        {"service": check.service, "remediation": check.remediation, "detail": check.detail}
        for check in checks
        if check.service in RUNTIME_MODES[selected].required_services and check.status != "real"
    ]
    safe_next = "make run-offline-fixture" if selected in ("offline_fixture", "ci_smoke") else "make run-best-effort"
    if not classification["can_continue"]:
        safe_next = "Fix required services listed in doctor_report.md"
    return {
        "requested_mode": requested_mode,
        "selected_runtime_mode": selected,
        "can_continue": classification["can_continue"],
        "services": [check.to_dict() for check in checks],
        "disabled_capabilities": classification["disabled_capabilities"],
        "fallbacks_used": classification["fallbacks_used"],
        "required_fixes": required_fixes,
        "safe_next_command": safe_next,
        "mode_policy": RUNTIME_MODES[selected].__dict__,
    }


def markdown(report: dict) -> str:
    lines = [
        "# AgentCo Doctor Report",
        "",
        f"- Requested mode: `{report['requested_mode']}`",
        f"- Selected runtime mode: `{report['selected_runtime_mode']}`",
        f"- Can continue: `{report['can_continue']}`",
        f"- Safe next command: `{report['safe_next_command']}`",
        "",
        "## Services",
        "",
        "| Service | Status | Detail | Remediation |",
        "|---|---|---|---|",
    ]
    for service in report["services"]:
        detail = str(service["detail"]).replace("\n", " ")[:180]
        remediation = str(service["remediation"]).replace("\n", " ")[:120]
        lines.append(f"| `{service['service']}` | `{service['status']}` | {detail} | {remediation} |")
    lines.extend(["", "## Fallbacks Used", ""])
    if report["fallbacks_used"]:
        for fallback in report["fallbacks_used"]:
            lines.append(f"- `{fallback['service']}` -> `{fallback['fallback']}` (`{fallback['status']}`)")
    else:
        lines.append("- None")
    lines.extend(["", "## Disabled Capabilities", ""])
    if report["disabled_capabilities"]:
        for item in report["disabled_capabilities"]:
            lines.append(f"- `{item}`")
    else:
        lines.append("- None")
    lines.extend(["", "## Required Fixes", ""])
    if report["required_fixes"]:
        for fix in report["required_fixes"]:
            lines.append(f"- `{fix['service']}`: {fix['remediation']} ({fix['detail']})")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "doctor_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (REPORT_DIR / "doctor_report.md").write_text(markdown(report))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local_native", choices=sorted(RUNTIME_MODES))
    parser.add_argument("--live-openai", action="store_true")
    parser.add_argument("--run-builds", action="store_true")
    args = parser.parse_args(argv)
    checks = collect_checks(args.mode, live_openai=args.live_openai, run_builds=args.run_builds)
    report = build_report(args.mode, checks)
    write_report(report)
    print(f"AgentCo doctor selected {report['selected_runtime_mode']} can_continue={report['can_continue']}")
    print(f"Report: {REPORT_DIR / 'doctor_report.md'}")
    return 0 if report["can_continue"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
