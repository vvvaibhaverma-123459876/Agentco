from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .modes import RUNTIME_MODES, choose_runtime_mode, classify_mode, production_capability_contract


ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "reports" / "system_run" / "latest"


@dataclass
class Check:
    service: str
    status: str
    detail: str
    remediation: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def run_cmd(cmd: list[str], cwd: Path = ROOT, timeout: int = 20) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, f"{' '.join(cmd)} timed out"


def check_port(port: int) -> bool:
    try:
        with socket.create_connection(("localhost", port), timeout=0.5):
            return True
    except OSError:
        return False


def check_python() -> Check:
    ok = sys.version_info[:2] == (3, 13)
    return Check("python", "real" if ok else "broken", sys.version.split()[0], "Use python3.13")


def check_pytest() -> Check:
    return Check("python_dependencies", "real" if importlib.util.find_spec("pytest") else "missing", "pytest importable" if importlib.util.find_spec("pytest") else "pytest missing", "Install requirements-dev.txt")


def check_binary(service: str, binary: str) -> Check:
    path = shutil.which(binary)
    return Check(service, "real" if path else "missing", path or f"{binary} not found")


def check_build(service: str, cwd: Path, run_builds: bool) -> Check:
    if not run_builds:
        return Check(service, "not_required", "build not run in this mode")
    code, out = run_cmd(["npm", "run", "build"], cwd=cwd, timeout=90)
    return Check(service, "real" if code == 0 else "broken", out[-500:], "Run npm run build")


def check_docker_daemon() -> Check:
    if not shutil.which("docker"):
        return Check("docker_daemon", "missing", "docker missing")
    code, out = run_cmd(["docker", "ps"], timeout=8)
    return Check("docker_daemon", "real" if code == 0 else "blocked", "docker daemon reachable" if code == 0 else out[:250], "Start Docker or use local_native")


def check_postgres() -> Check:
    db_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or "postgresql://agentco:password@localhost:5432/agentco"
    code, out = run_cmd(["psql", db_url, "-Atc", "select current_database(), current_user"], timeout=8)
    return Check("postgres", "real" if code == 0 else "missing", out[:250], "Start native Postgres or use offline_fixture")


def check_schema() -> Check:
    db_url = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL") or "postgresql://agentco:password@localhost:5432/agentco"
    sql = "select to_regclass('public.prediction_ledger'), to_regclass('public.decision_log'), to_regclass('public.override_queue')"
    code, out = run_cmd(["psql", db_url, "-Atc", sql], timeout=8)
    ok = code == 0 and "prediction_ledger" in out and "decision_log" in out and "override_queue" in out
    return Check("core_db_schema", "real" if ok else "broken", out[:250], "Run make verify-migrations-native")


def check_migrations() -> Check:
    pkg = ROOT / "backend" / "package.json"
    if not pkg.exists():
        return Check("migrations", "missing", "backend/package.json missing")
    data = json.loads(pkg.read_text())
    script = data.get("scripts", {}).get("db:migrate", "")
    return Check("migrations", "real" if "ts-node src/db/migrate.ts" in script else "broken", script, "Use TypeScript migration runner")


def check_tcp(service: str, port: int, remediation: str) -> Check:
    return Check(service, "real" if check_port(port) else "missing", f"localhost:{port}", remediation)


def check_openai_env() -> Check:
    present = bool(os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"))
    return Check("openai_env", "real" if present else "missing", f"key_present={present}", "Set LLM_API_KEY or use offline")


def check_production_secret_posture() -> Check:
    env = os.environ
    failures: list[str] = []
    dev_values = {
        "AGENTCO_API_KEY": {"", "dev-api-key"},
        "EVENT_BUS_SIGNING_KEY": {"", "dev-key-replace-in-production"},
        "EVENT_BUS_HMAC_KEY": {"", "dev-insecure-key"},
        "JWT_SECRET": {"", "change-me-generate-with-openssl-rand-hex-64"},
        "VAULT_TOKEN": {"", "root"},
        "RESERVE_SIGNING_KEY": {"dev-insecure-key"},
    }
    for key, rejected in dev_values.items():
        if env.get(key, "") in rejected:
            failures.append(key)
    for key in ("DATABASE_URL", "AGENTCO_TEST_DATABASE_URL"):
        value = env.get(key, "")
        if "://agentco:password@" in value or "://postgres:password@" in value:
            failures.append(key)
    if failures:
        return Check(
            "production_secret_posture",
            "blocked",
            "dev-default or missing production secrets: " + ", ".join(sorted(set(failures))),
            "Set non-default production secrets through Vault or the deployment secret manager",
        )
    return Check("production_secret_posture", "real", "no dev-default production secrets detected")


def check_openai_connectivity(live: bool) -> Check:
    if not live:
        return Check("openai_connectivity", "not_required", "live check not requested")
    script = ROOT / "scripts" / "verify_openai_connectivity.py"
    if not script.exists():
        return Check("openai_connectivity", "missing", "verify_openai_connectivity.py missing")
    code, out = run_cmd([sys.executable, str(script)], timeout=45)
    return Check("openai_connectivity", "real" if code == 0 else "broken", out[-500:])


def check_resolution_service() -> Check:
    db_url = os.getenv("RESOLUTION_SERVICE_DATABASE_URL")
    if not db_url:
        base = os.getenv("DATABASE_URL") or os.getenv("AGENTCO_TEST_DATABASE_URL")
        if base:
            from urllib.parse import quote, urlparse
            parsed = urlparse(base)
            password = os.getenv("RESOLUTION_SERVICE_PASSWORD", "resolution-service-dev-password")
            db_url = f"postgresql://resolution_service:{quote(password, safe='')}@{parsed.hostname or 'localhost'}:{parsed.port or 5432}/{parsed.path.lstrip('/') or 'agentco'}"
    if not db_url:
        return Check("resolution_service", "missing", "no resolution service DSN")
    code, out = run_cmd(["psql", db_url, "-Atc", "select current_user"], timeout=8)
    return Check("resolution_service", "real" if code == 0 and "resolution_service" in out else "blocked", out[:250], "Set RESOLUTION_SERVICE_DATABASE_URL")


def check_sensitive_route_auth() -> Check:
    route = ROOT / "backend" / "src" / "routes" / "override.routes.ts"
    text = route.read_text() if route.exists() else ""
    ok = "fastify.get('/api/overrides', { preHandler: requireApiKey }" in text
    return Check("sensitive_route_auth", "real" if ok else "broken", "override read route protected" if ok else "override read route lacks preHandler", "Protect override reads")


def check_reports_dir() -> Check:
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        probe = REPORT_DIR / ".write_probe"
        probe.write_text("ok\n")
        probe.unlink()
        return Check("filesystem_reports", "real", str(REPORT_DIR))
    except OSError as exc:
        return Check("filesystem_reports", "broken", str(exc))


def collect_checks(mode: str, live_openai: bool = False, run_builds: bool = False) -> list[Check]:
    load_env_file(ROOT / ".codex.env")
    return [
        check_python(),
        check_pytest(),
        check_binary("node", "node"),
        check_binary("npm", "npm"),
        check_build("backend_build", ROOT / "backend", run_builds),
        check_build("frontend_build", ROOT / "frontend", run_builds),
        check_binary("docker_cli", "docker"),
        check_docker_daemon(),
        check_postgres(),
        check_migrations(),
        check_schema(),
        check_tcp("redis", 6379, "Use memory cache fallback"),
        check_tcp("kafka", 9092, "Use in-process event bus fallback"),
        check_tcp("vault", 8200, "Use env secret provider fallback"),
        check_tcp("prometheus", 9090, "Use JSON metrics fallback"),
        check_tcp("grafana", 3005, "Skip dashboard UI"),
        check_openai_env(),
        check_openai_connectivity(live_openai),
        check_resolution_service(),
        check_sensitive_route_auth(),
        check_production_secret_posture(),
        check_reports_dir(),
    ]


def build_report(requested_mode: str, checks: list[Check]) -> dict:
    status = {c.service: c.status for c in checks}
    selected = choose_runtime_mode(requested_mode, status)
    if requested_mode in ("offline_fixture", "ci_smoke"):
        selected = requested_mode
    classified = classify_mode(selected, status)
    required_fixes = [
        {"service": c.service, "detail": c.detail, "remediation": c.remediation}
        for c in checks
        if c.service in RUNTIME_MODES[selected].required_services and c.status != "real"
    ]
    return {
        "requested_mode": requested_mode,
        "selected_runtime_mode": selected,
        "can_continue": classified["can_continue"],
        "production_contract": production_capability_contract(status),
        "services": [c.to_dict() for c in checks],
        "fallbacks_used": classified["fallbacks_used"],
        "disabled_capabilities": classified["disabled_capabilities"],
        "required_fixes": required_fixes,
        "safe_next_command": "make run-offline-fixture" if selected in ("offline_fixture", "ci_smoke") else "make run-best-effort",
    }


def write_report(report: dict) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "doctor_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    lines = [
        "# AgentCo Doctor Report",
        "",
        f"- Requested mode: `{report['requested_mode']}`",
        f"- Selected runtime mode: `{report['selected_runtime_mode']}`",
        f"- Can continue: `{report['can_continue']}`",
        f"- Safe next command: `{report['safe_next_command']}`",
        "",
        "| Service | Status | Detail |",
        "|---|---|---|",
    ]
    for svc in report["services"]:
        lines.append(f"| `{svc['service']}` | `{svc['status']}` | {str(svc['detail']).replace(chr(10), ' ')[:180]} |")
    lines.extend(["", "## Fallbacks Used"])
    lines.extend([f"- `{f['service']}` -> `{f['fallback']}` (`{f['status']}`)" for f in report["fallbacks_used"]] or ["- None"])
    lines.extend(["", "## Disabled Capabilities"])
    lines.extend([f"- `{d}`" for d in report["disabled_capabilities"]] or ["- None"])
    (REPORT_DIR / "doctor_report.md").write_text("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="local_native", choices=sorted(RUNTIME_MODES))
    parser.add_argument("--live-openai", action="store_true")
    parser.add_argument("--run-builds", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.mode, collect_checks(args.mode, args.live_openai, args.run_builds))
    write_report(report)
    print(f"AgentCo doctor selected {report['selected_runtime_mode']} can_continue={report['can_continue']}")
    return 0 if report["can_continue"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
