#!/usr/bin/env python3
"""Run the isolated clean-room audit with owned PostgreSQL and evidence."""

from __future__ import annotations

import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import sys
import time
from difflib import unified_diff
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

try:
    from verify_migration_integrity import schema_dump, schema_fingerprint
except ModuleNotFoundError:  # pragma: no cover - exercised when imported as scripts.audit_clean_room
    from scripts.verify_migration_integrity import schema_dump, schema_fingerprint


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "audit"
POSTGRES_IMAGE = os.environ.get("AGENTCO_AUDIT_POSTGRES_IMAGE", "postgres:16-alpine")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class CommandRecord:
    command_id: str
    argv: list[str]
    cwd: str
    environment_names: list[str]
    start_time: str
    end_time: str
    duration_seconds: float
    exit_code: int
    stdout_artifact: str
    stderr_artifact: str
    run_id: str
    commit: str


@dataclass
class CleanRoomState:
    run_id: str
    run_dir: Path
    commands_dir: Path
    migration_dir: Path
    test_dir: Path
    container: str
    volume: str
    database: str
    username: str
    password: str
    host_port: str | None = None
    commands: list[CommandRecord] = field(default_factory=list)
    cleanup: dict[str, object] = field(default_factory=dict)

    @property
    def database_url(self) -> str:
        if not self.host_port:
            raise RuntimeError("Postgres host port has not been discovered")
        return f"postgresql://{self.username}:{self.password}@127.0.0.1:{self.host_port}/{self.database}"

    @property
    def admin_url(self) -> str:
        if not self.host_port:
            raise RuntimeError("Postgres host port has not been discovered")
        return f"postgresql://{self.username}:{self.password}@127.0.0.1:{self.host_port}/postgres"


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


SECRET_PATTERNS = ("PASSWORD", "TOKEN", "SECRET", "API_KEY", "AUTHORIZATION")


def redact_value(value: str) -> str:
    text = re.sub(r"(postgres(?:ql)?://[^:/@\s]+:)([^@\s]+)(@)", r"\1<redacted>\3", value)
    text = re.sub(r"((?:PASSWORD|TOKEN|SECRET|API_KEY|AUTHORIZATION)=)([^\s]+)", r"\1<redacted>", text, flags=re.IGNORECASE)
    return text


def redact_argv(argv: list[str]) -> list[str]:
    return [redact_value(item) for item in argv]


def env_names(env: dict[str, str] | None) -> list[str]:
    return sorted((env or {}).keys())


def command_artifact_paths(state: CleanRoomState, command_id: str) -> tuple[Path, Path]:
    index = len(state.commands) + 1
    stdout_path = state.commands_dir / f"{index:03d}_{command_id}.stdout.txt"
    stderr_path = state.commands_dir / f"{index:03d}_{command_id}.stderr.txt"
    return stdout_path, stderr_path


def run_command(
    state: CleanRoomState,
    command_id: str,
    command: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    required: bool = True,
) -> int:
    if any(existing.command_id == command_id for existing in state.commands):
        raise RuntimeError(f"duplicate command id: {command_id}")
    stdout_path, stderr_path = command_artifact_paths(state, command_id)
    start_monotonic = time.monotonic()
    start_time = utc_now()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    completed = subprocess.run(
        command,
        cwd=cwd or ROOT,
        env=merged_env,
        text=True,
        capture_output=True,
    )
    end_time = utc_now()
    duration = round(time.monotonic() - start_monotonic, 3)
    stdout_path.write_text(completed.stdout or "")
    stderr_path.write_text(completed.stderr or "")
    record = CommandRecord(
        command_id=command_id,
        argv=redact_argv(command),
        cwd=str((cwd or ROOT).relative_to(ROOT) if (cwd or ROOT).is_relative_to(ROOT) else cwd or ROOT),
        environment_names=env_names(env),
        start_time=start_time,
        end_time=end_time,
        duration_seconds=duration,
        exit_code=int(completed.returncode),
        stdout_artifact=str(stdout_path.relative_to(state.run_dir)),
        stderr_artifact=str(stderr_path.relative_to(state.run_dir)),
        run_id=state.run_id,
        commit=git(["rev-parse", "HEAD"]),
    )
    state.commands.append(record)
    if required and completed.returncode != 0:
        raise RuntimeError(f"{command_id} failed with exit code {completed.returncode}")
    return int(completed.returncode)


def quiet_output(command: list[str], env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.check_output(command, cwd=ROOT, env=merged_env, text=True, stderr=subprocess.STDOUT).strip()


def ensure_git_clean() -> None:
    status = quiet_output(["git", "status", "--porcelain"])
    if status:
        raise RuntimeError(f"working tree is dirty:\n{status}")


def make_state() -> CleanRoomState:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    token = secrets.token_hex(4)
    run_id = f"{stamp}-{token}"
    run_dir = ARTIFACT_ROOT / run_id
    state = CleanRoomState(
        run_id=run_id,
        run_dir=run_dir,
        commands_dir=run_dir / "commands",
        migration_dir=run_dir / "migration-results",
        test_dir=run_dir / "test-results",
        container=f"agentco-audit-pg-{run_id.lower()}",
        volume=f"agentco-audit-pg-{run_id.lower()}",
        database=f"agentco_audit_{token}",
        username="agentco",
        password=secrets.token_urlsafe(18),
    )
    state.commands_dir.mkdir(parents=True)
    state.migration_dir.mkdir(parents=True)
    state.test_dir.mkdir(parents=True)
    return state


def start_postgres(state: CleanRoomState) -> None:
    run_command(
        state,
        "docker-postgres-start",
        [
            "docker",
            "run",
            "-d",
            "--name",
            state.container,
            "-e",
            f"POSTGRES_USER={state.username}",
            "-e",
            f"POSTGRES_PASSWORD={state.password}",
            "-p",
            "127.0.0.1::5432",
            "-v",
            f"{state.volume}:/var/lib/postgresql/data",
            POSTGRES_IMAGE,
        ],
    )
    state.host_port = quiet_output(["docker", "port", state.container, "5432/tcp"]).rsplit(":", 1)[-1]
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            quiet_output(["pg_isready", "-h", "127.0.0.1", "-p", state.host_port, "-U", state.username])
            return
        except subprocess.CalledProcessError:
            time.sleep(1)
    raise RuntimeError("PostgreSQL container did not become ready within 60 seconds")


def write_runtime_summary(state: CleanRoomState, verdict: str, error: str | None) -> None:
    commit = git(["rev-parse", "HEAD"])
    ledger = {
        "run_id": state.run_id,
        "commit": commit,
        "branch": git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "working_tree": "dirty" if git(["status", "--porcelain"]) else "clean",
        "start_time": state.commands[0].start_time if state.commands else utc_now(),
        "completion_time": utc_now(),
        "host_platform": platform.platform(),
        "architecture": platform.machine(),
        "python_version": sys.version,
        "node_version": shutil.which("node") and quiet_output(["node", "--version"]),
        "npm_version": shutil.which("npm") and quiet_output(["npm", "--version"]),
        "docker_version": shutil.which("docker") and quiet_output(["docker", "--version"]),
        "postgres_image": POSTGRES_IMAGE,
        "database_container": state.container,
        "database_volume": state.volume,
        "database_name": state.database,
        "commands": [asdict(command) for command in state.commands],
        "cleanup": state.cleanup,
        "final_verdict": verdict,
        "error": error,
    }
    ledger_path = state.run_dir / "EXECUTION_LEDGER.json"
    ledger_path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    (state.run_dir / "AUDIT_SUMMARY.md").write_text(
        "\n".join(
            [
                "# Clean-Room Audit Summary",
                "",
                f"Run ID: `{state.run_id}`",
                f"Commit: `{commit}`",
                f"Branch: `{ledger['branch']}`",
                f"Verdict: `{verdict}`",
                f"Database container: `{state.container}`",
                f"Database name: `{state.database}`",
                f"Commands recorded: `{len(state.commands)}`",
                f"Cleanup: `{state.cleanup}`",
                f"Error: `{error or 'none'}`",
                "",
                "This is runtime execution evidence. It is ignored by Git and must not be treated as a tracked structural snapshot.",
            ]
        )
        + "\n"
    )


def cleanup(state: CleanRoomState) -> bool:
    results: dict[str, object] = {}
    env = {"PGPASSWORD": state.password, "PGHOST": "127.0.0.1", "PGPORT": state.host_port or "", "PGUSER": state.username}
    ok = True
    if not state.host_port:
        results["cleanup-drop-database"] = {"exit_code": 127, "skipped": "postgres port unavailable"}
        ok = False
    else:
        code = run_command(state, "cleanup-drop-database", ["dropdb", "--if-exists", state.database], env=env, required=False)
        results["cleanup-drop-database"] = {"exit_code": code}
        if code != 0:
            ok = False

    for command_id, command in [
        ("cleanup-remove-container", ["docker", "rm", "-f", state.container]),
        ("cleanup-remove-volume", ["docker", "volume", "rm", state.volume]),
        ("cleanup-verify-container-removed", ["docker", "container", "inspect", state.container]),
        ("cleanup-verify-volume-removed", ["docker", "volume", "inspect", state.volume]),
    ]:
        code = run_command(state, command_id, command, required=False)
        absent_check = command_id.startswith("cleanup-verify-")
        success = code != 0 if absent_check else code == 0
        results[command_id] = {"exit_code": code, "success": success}
        if not success:
            ok = False
    state.cleanup = {"success": ok, "steps": results}
    return ok


def run_release_components_once(state: CleanRoomState, env: dict[str, str]) -> None:
    run_command(state, "release-gate-integrity", [sys.executable, "scripts/verify_gate_integrity.py", "--check"])
    run_command(state, "release-make-targets", [sys.executable, "scripts/verify_make_targets.py", "--check"])
    run_command(state, "release-status-check", ["make", "status-check"])
    run_command(state, "release-agent-protocol-matrix-check", ["make", "agent-protocol-matrix-check"])
    run_command(state, "release-evaluation-calibration-report-check", ["make", "evaluation-calibration-report-check"])
    run_command(state, "release-controlled-learning-report-check", ["make", "controlled-learning-report-check"])
    run_command(state, "release-self-improvement-report-check", ["make", "self-improvement-report-check"])
    run_command(state, "release-score-validation", ["npm", "run", "agentco:score-validation", "--", "--check"], cwd=ROOT / "backend")
    run_command(
        state,
        "pytest-governed",
        [
            sys.executable,
            "scripts/verify_pytest_skips.py",
            "--report",
            str(state.test_dir / "pytest-report.json"),
            "--summary-output",
            str(state.test_dir / "pytest-summary.json"),
            "--",
            "-q",
        ],
        env=env,
    )
    run_command(state, "backend-build", ["npm", "run", "build"], cwd=ROOT / "backend")
    run_command(state, "backend-jest", ["npm", "test", "--", "--runInBand"], cwd=ROOT / "backend", env=env)
    run_command(state, "backend-route-auth-contract", ["npm", "test", "--", "route-auth-contract.test.ts", "--runInBand"], cwd=ROOT / "backend", env=env)
    run_command(state, "backend-audit-chain-cross-writer", ["npm", "test", "--", "audit-chain-cross-writer.test.ts", "--runInBand"], cwd=ROOT / "backend", env=env)
    run_command(state, "frontend-install", ["npm", "ci"], cwd=ROOT / "frontend")
    run_command(state, "frontend-typecheck", ["./node_modules/.bin/tsc", "--noEmit"], cwd=ROOT / "frontend")
    run_command(state, "frontend-build", ["npm", "run", "build"], cwd=ROOT / "frontend", env={"NEXT_TELEMETRY_DISABLED": "1"})


def main() -> int:
    state = make_state()
    error: str | None = None
    verdict = "FAIL"
    env: dict[str, str] = {}
    try:
        ensure_git_clean()
        run_command(state, "docker-version", ["docker", "--version"])
        start_postgres(state)
        env = {
            "DATABASE_URL": state.database_url,
            "AGENTCO_TEST_DATABASE_URL": state.database_url,
            "RELEASE_GATE_DATABASE_URL": state.database_url,
            "RELEASE_GATE_MIGRATION_DATABASE_URL": state.database_url,
            "RESOLUTION_SERVICE_PASSWORD": "test",
            "AGENTCO_ALLOW_DESTRUCTIVE_RESERVE_TESTS": "1",
            "AGENTCO_ALLOW_DESTRUCTIVE_MIGRATION_TESTS": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        run_command(state, "create-database", ["createdb", state.database], env={"PGPASSWORD": state.password, "PGHOST": "127.0.0.1", "PGPORT": state.host_port or "", "PGUSER": state.username})
        run_command(
            state,
            "migration-static-integrity",
            [sys.executable, "scripts/verify_migration_integrity.py", "--json-output", str(state.migration_dir / "static.json")],
        )
        run_command(
            state,
            "database-empty-before-migration",
            [
                sys.executable,
                "scripts/verify_migration_integrity.py",
                "--database-url",
                state.database_url,
                "--expect-empty",
                "--json-output",
                str(state.migration_dir / "before.json"),
            ],
        )
        run_command(state, "backend-install", ["npm", "ci"], cwd=ROOT / "backend")
        run_command(state, "migrate-from-zero", ["npm", "run", "db:migrate"], cwd=ROOT / "backend", env=env)
        before_second = schema_fingerprint(state.database_url)
        before_second_dump = schema_dump(state.database_url)
        run_command(
            state,
            "database-after-migration",
            [
                sys.executable,
                "scripts/verify_migration_integrity.py",
                "--database-url",
                state.database_url,
                "--after-migration",
                "--json-output",
                str(state.migration_dir / "after.json"),
            ],
        )
        run_command(state, "migrate-idempotency-second-run", ["npm", "run", "db:migrate"], cwd=ROOT / "backend", env=env)
        after_second = schema_fingerprint(state.database_url)
        after_second_dump = schema_dump(state.database_url)
        idempotency = {"before": before_second, "after": after_second, "success": before_second == after_second}
        (state.migration_dir / "idempotency.json").write_text(json.dumps(idempotency, indent=2, sort_keys=True) + "\n")
        if before_second != after_second:
            before_path = state.migration_dir / "schema-before-second.sql"
            after_path = state.migration_dir / "schema-after-second.sql"
            diff_path = state.migration_dir / "schema-second-run.diff"
            before_path.write_text(before_second_dump)
            after_path.write_text(after_second_dump)
            diff_path.write_text(
                "".join(
                    unified_diff(
                        before_second_dump.splitlines(keepends=True),
                        after_second_dump.splitlines(keepends=True),
                        fromfile=str(before_path.name),
                        tofile=str(after_path.name),
                    )
                )
            )
            raise RuntimeError("second migration run changed schema fingerprint")
        run_release_components_once(state, env)
        ensure_git_clean()
        verdict = "PASS"
    except Exception as exc:
        error = str(exc)
    finally:
        cleanup_ok = cleanup(state)
        if not cleanup_ok:
            verdict = "FAIL"
            error = (error + "; " if error else "") + "cleanup failed"
        write_runtime_summary(state, verdict, error)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
