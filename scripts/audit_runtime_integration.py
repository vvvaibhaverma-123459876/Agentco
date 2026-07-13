#!/usr/bin/env python3
"""Batch 03 local runtime integration audit.

Starts real local PostgreSQL, Redis, Zookeeper, and Kafka containers; runs
migrations; exercises backend health, Redis, Kafka, transactional outbox,
Python specialist dispatch, restart/idempotency checks, and cleanup.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "runtime-integration"
SECRET_PATTERNS = [
    re.compile(r"postgresql://([^:\s]+):([^@\s]+)@"),
    re.compile(r"(?i)(password|token|api[_-]?key|authorization)=([^\s]+)"),
]


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def available_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def redact(value: str) -> str:
    out = value
    out = SECRET_PATTERNS[0].sub(r"postgresql://\1:<redacted>@", out)
    out = SECRET_PATTERNS[1].sub(lambda m: f"{m.group(1)}=<redacted>", out)
    return out


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
class State:
    run_id: str
    commit: str
    branch: str
    artifact_dir: Path
    command_dir: Path
    logs_dir: Path
    traces_dir: Path
    cleanup_dir: Path
    network: str
    pg_container: str
    redis_container: str
    zk_container: str
    kafka_container: str
    pg_volume: str
    redis_volume: str
    kafka_volume: str
    zk_volume: str
    pg_port: int
    redis_port: int
    kafka_port: int
    backend_port: int
    db_password: str
    commands: list[CommandRecord] = field(default_factory=list)
    cleanup: dict[str, Any] = field(default_factory=dict)
    workflow_results: dict[str, Any] = field(default_factory=dict)
    final_verdict: str = "FAIL"

    @property
    def database_url(self) -> str:
        return f"postgresql://agentco:{self.db_password}@127.0.0.1:{self.pg_port}/agentco"

    @property
    def redis_url(self) -> str:
        return f"redis://127.0.0.1:{self.redis_port}"

    @property
    def kafka_brokers(self) -> str:
        return f"127.0.0.1:{self.kafka_port}"


def git(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def command_env(env: dict[str, str] | None) -> list[str]:
    return sorted((env or {}).keys())


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(redact(value))


def run(state: State, command_id: str, argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, timeout: int = 120, allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    start = time.time()
    started = utc()
    proc = subprocess.run(
        argv,
        cwd=cwd or ROOT,
        env={**os.environ, **(env or {})},
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    ended = utc()
    stdout_rel = f"commands/{len(state.commands) + 1:03d}_{command_id}.stdout.txt"
    stderr_rel = f"commands/{len(state.commands) + 1:03d}_{command_id}.stderr.txt"
    write_text(state.artifact_dir / stdout_rel, proc.stdout)
    write_text(state.artifact_dir / stderr_rel, proc.stderr)
    state.commands.append(CommandRecord(
        command_id=command_id,
        argv=[redact(part) for part in argv],
        cwd=str((cwd or ROOT).relative_to(ROOT) if (cwd or ROOT).is_relative_to(ROOT) else cwd or ROOT),
        environment_names=command_env(env),
        start_time=started,
        end_time=ended,
        duration_seconds=round(time.time() - start, 3),
        exit_code=proc.returncode,
        stdout_artifact=stdout_rel,
        stderr_artifact=stderr_rel,
        run_id=state.run_id,
        commit=state.commit,
    ))
    if proc.returncode != 0 and not allow_failure:
        raise RuntimeError(f"{command_id} failed with {proc.returncode}; see {stdout_rel}/{stderr_rel}")
    return proc


def wait_until(label: str, timeout: int, probe) -> None:
    start = time.time()
    last: Exception | None = None
    while time.time() - start < timeout:
        try:
            if probe():
                return
        except Exception as exc:  # bounded wait probe, surfaced on timeout
            last = exc
        time.sleep(1)
    raise TimeoutError(f"{label} did not become ready within {timeout}s: {last}")


def docker_run(state: State, command_id: str, argv: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return run(state, command_id, ["docker", *argv], timeout=timeout)


def start_services(state: State) -> None:
    docker_run(state, "docker-network-create", ["network", "create", state.network])
    for volume in [state.pg_volume, state.redis_volume, state.zk_volume, state.kafka_volume]:
        docker_run(state, f"docker-volume-create-{volume.rsplit('-', 1)[-1]}", ["volume", "create", volume])
    docker_run(state, "postgres-start", [
        "run", "-d", "--name", state.pg_container, "--network", state.network,
        "-p", f"127.0.0.1:{state.pg_port}:5432",
        "-e", "POSTGRES_USER=agentco",
        "-e", f"POSTGRES_PASSWORD={state.db_password}",
        "-e", "POSTGRES_DB=agentco",
        "-v", f"{state.pg_volume}:/var/lib/postgresql/data",
        "postgres:16-alpine",
    ])
    docker_run(state, "redis-start", [
        "run", "-d", "--name", state.redis_container, "--network", state.network,
        "-p", f"127.0.0.1:{state.redis_port}:6379",
        "-v", f"{state.redis_volume}:/data",
        "redis:7-alpine", "redis-server", "--save", "60", "1", "--loglevel", "warning",
    ])
    docker_run(state, "zookeeper-start", [
        "run", "-d", "--name", state.zk_container, "--network", state.network,
        "-e", "ZOOKEEPER_CLIENT_PORT=2181",
        "-e", "ZOOKEEPER_TICK_TIME=2000",
        "-e", "ZOOKEEPER_SYNC_LIMIT=2",
        "-e", "ZOOKEEPER_4LW_COMMANDS_WHITELIST=ruok,srvr,stat,mntr",
        "confluentinc/cp-zookeeper:7.6.1",
    ])
    wait_until("postgres", 60, lambda: run(state, "postgres-ready-probe", ["docker", "exec", state.pg_container, "pg_isready", "-U", "agentco", "-d", "agentco"], allow_failure=True).returncode == 0)
    wait_until("redis", 60, lambda: run(state, "redis-ready-probe", ["docker", "exec", state.redis_container, "redis-cli", "ping"], allow_failure=True).stdout.strip() == "PONG")
    wait_until("zookeeper", 90, lambda: run(state, "zookeeper-ready-probe", [
        "docker", "exec", state.zk_container, "bash", "-ec",
        "exec 3<>/dev/tcp/localhost/2181; printf srvr >&3; IFS= read -r line <&3; case \"$line\" in \"Zookeeper version:\"*) exit 0;; *) exit 1;; esac",
    ], allow_failure=True).returncode == 0)
    docker_run(state, "kafka-start", [
        "run", "-d", "--name", state.kafka_container, "--network", state.network,
        "-p", f"127.0.0.1:{state.kafka_port}:9092",
        "-e", "KAFKA_BROKER_ID=1",
        "-e", f"KAFKA_ZOOKEEPER_CONNECT={state.zk_container}:2181",
        "-e", "KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:29092,PLAINTEXT_HOST://0.0.0.0:9092",
        "-e", "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT",
        "-e", f"KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://{state.kafka_container}:29092,PLAINTEXT_HOST://127.0.0.1:{state.kafka_port}",
        "-e", "KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT",
        "-e", "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1",
        "-e", "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1",
        "-e", "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1",
        "-e", "KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS=0",
        "-e", "KAFKA_AUTO_CREATE_TOPICS_ENABLE=true",
        "-v", f"{state.kafka_volume}:/var/lib/kafka/data",
        "confluentinc/cp-kafka:7.6.1",
    ], timeout=180)
    wait_until("kafka", 120, lambda: run(state, "kafka-ready-probe", ["docker", "exec", state.kafka_container, "kafka-topics", "--bootstrap-server", "localhost:29092", "--list"], allow_failure=True, timeout=30).returncode == 0)


def runtime_env(state: State) -> dict[str, str]:
    return {
        "DATABASE_URL": state.database_url,
        "AGENTCO_TEST_DATABASE_URL": state.database_url,
        "REDIS_URL": state.redis_url,
        "KAFKA_BROKERS": state.kafka_brokers,
        "KAFKA_MANDATORY": "1",
        "KAFKA_RETRIES": "4",
        "KAFKA_INITIAL_RETRY_MS": "200",
        "HEALTH_CHECK_TIMEOUT_MS": "7000",
        "KAFKAJS_NO_PARTITIONER_WARNING": "1",
        "AGENTCO_API_KEY": "runtime-integration-key",
        "FRONTEND_URL": "http://127.0.0.1:3000",
        "EVENT_BUS_SIGNING_KEY": "runtime-integration-signing-key",
        "PORT": str(state.backend_port),
        "HOST": "127.0.0.1",
        "PYTHONPATH": str(ROOT),
        "AGENTCO_PYTHON": sys.executable,
    }


def run_backend_server(state: State) -> subprocess.Popen[str]:
    env = {**os.environ, **runtime_env(state)}
    proc = subprocess.Popen(
        ["node", "dist/server.js"],
        cwd=ROOT / "backend",
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc


def collect_process_logs(state: State, name: str, proc: subprocess.Popen[str]) -> None:
    try:
        out, err = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate(timeout=5)
    write_text(state.logs_dir / f"{name}.stdout.txt", out or "")
    write_text(state.logs_dir / f"{name}.stderr.txt", err or "")


def http_get(url: str, headers: dict[str, str] | None = None, timeout: int = 10) -> tuple[int, str]:
    import urllib.request
    request = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode()
    except Exception as exc:
        if hasattr(exc, "code"):
            return int(exc.code), exc.read().decode()  # type: ignore[attr-defined]
        raise


def write_ts_probe() -> Path:
    probe = ROOT / "backend" / ".runtime-integration" / "runtime-integration-probe.ts"
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text(
        """
import crypto from 'crypto';
import Redis from 'ioredis';
import { db } from '../src/db/client';
import { createConsumer, disconnectProducer } from '../src/db/kafka';
import { EventLogService } from '../src/services/event-log.service';
import { OutboxWorker } from '../src/workers/outbox-worker';
import { shutdownRuntimeResources } from '../src/runtime/shutdown';

async function main() {
  const mode = process.argv[2];
  const correlation = process.env.RUNTIME_INTEGRATION_CORRELATION_ID || crypto.randomUUID();
  if (mode === 'redis') {
    const redis = new Redis(process.env.REDIS_URL!);
    await redis.set(`agentco:${correlation}`, 'ok');
    const value = await redis.get(`agentco:${correlation}`);
    await redis.quit();
    console.log(JSON.stringify({ mode, value }));
    return;
  }
  if (mode === 'kafka-health') {
    const { checkKafkaHealth } = require('../src/db/kafka');
    await checkKafkaHealth();
    console.log(JSON.stringify({ mode, brokers: process.env.KAFKA_BROKERS }));
    return;
  }
  if (mode === 'outbox') {
    const actorId = crypto.randomUUID();
    await db.query(`INSERT INTO actors (id, actor_type, name, status, metadata_json) VALUES ($1,'service','Runtime Probe','active',$2::jsonb) ON CONFLICT (id) DO NOTHING`, [actorId, JSON.stringify({ source: 'runtime-integration' })]);
    const eventLog = new EventLogService();
    const objectId = crypto.randomUUID();
    const event = await eventLog.append({
      event_type: 'test.runtime_integration',
      actor_id: actorId,
      object_type: 'runtime_probe',
      object_id: objectId,
      payload: { correlation },
      correlation_id: correlation,
    });
    const before = await db.query(`SELECT status FROM event_outbox WHERE event_log_id=$1`, [event.id]);
    const worker = new OutboxWorker({
      pollIntervalMs: 100,
      batchSize: 10,
      maxAttempts: 3,
      workerId: `runtime-integration-${process.pid}`,
      once: true,
    });
    const result = await worker.runOnce();
    const after = await db.query(`SELECT status, attempts FROM event_outbox WHERE event_log_id=$1`, [event.id]);
    console.log(JSON.stringify({ mode, correlation, event_id: event.id, before: before.rows, relay: result, after: after.rows }));
    await disconnectProducer();
    await shutdownRuntimeResources({ closeDb: true });
    return;
  }
  if (mode === 'consume') {
    const topic = 'agentco.test';
    const consumer = createConsumer(`runtime-integration-${Date.now()}`);
    const seen: any[] = [];
    await consumer.connect();
    await consumer.subscribe({ topic, fromBeginning: true });
    await consumer.run({
      eachMessage: async ({ message }: { message: { value: Buffer | null } }) => {
        if (!message.value) return;
        const parsed = JSON.parse(message.value.toString());
        if (parsed.correlation_id === correlation) seen.push(parsed);
      },
    });
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline && seen.length === 0) await new Promise(r => setTimeout(r, 250));
    await consumer.disconnect();
    console.log(JSON.stringify({ mode, correlation, seen_count: seen.length, event_ids: seen.map(e => e.event_id) }));
    if (seen.length === 0) process.exit(2);
    return;
  }
  if (mode === 'failure') {
    const actorId = crypto.randomUUID();
    await db.query(`INSERT INTO actors (id, actor_type, name, status, metadata_json) VALUES ($1,'service','Runtime Failure Probe','active',$2::jsonb) ON CONFLICT (id) DO NOTHING`, [actorId, JSON.stringify({ source: 'runtime-integration-failure' })]);
    const eventLog = new EventLogService();
    const event = await eventLog.append({
      event_type: 'test.runtime_integration_failure',
      actor_id: actorId,
      object_type: 'runtime_probe',
      object_id: crypto.randomUUID(),
      payload: { correlation },
      correlation_id: correlation,
    });
    const worker = new OutboxWorker({
      pollIntervalMs: 100,
      batchSize: 10,
      maxAttempts: 1,
      workerId: `runtime-integration-failure-${process.pid}`,
      once: true,
    }, {
      publisher: { publish: async () => { throw new Error('intentional broker failure'); } },
      relayEventLog: (publisher: unknown, options: unknown) => new (require('../src/services/transactional-outbox.service').TransactionalOutboxService)().relayBatch(publisher, options),
      relayEventBus: async () => ({ published: 0, failed: 0, dead_lettered: 0 }),
      shutdown: async () => {},
    });
    const result = await worker.runOnce();
    const row = await db.query(`SELECT status, attempts, last_error FROM event_outbox WHERE event_log_id=$1`, [event.id]);
    console.log(JSON.stringify({ mode, correlation, event_id: event.id, result, row: row.rows }));
    await shutdownRuntimeResources({ closeDb: true });
    return;
  }
  if (mode === 'restart-check') {
    const worker = new OutboxWorker({
      pollIntervalMs: 100,
      batchSize: 10,
      maxAttempts: 3,
      workerId: `runtime-integration-restart-${process.pid}`,
      once: true,
    });
    const result = await worker.runOnce();
    const rows = await db.query(`SELECT status, attempts FROM event_outbox WHERE envelope->>'correlation_id'=$1 ORDER BY created_at`, [correlation]);
    console.log(JSON.stringify({ mode, correlation, relay: result, rows: rows.rows }));
    await disconnectProducer();
    await shutdownRuntimeResources({ closeDb: true });
    return;
  }
  throw new Error(`unknown mode ${mode}`);
}
main().catch(error => {
  console.error(error);
  process.exit(1);
});
""".strip() + "\n"
    )
    return probe


def run_workflows(state: State) -> None:
    env = runtime_env(state)
    probe = write_ts_probe()
    probe_arg = str(probe.relative_to(ROOT / "backend"))
    run(state, "backend-install", ["npm", "ci"], cwd=ROOT / "backend", timeout=180)
    run(state, "backend-build", ["npm", "run", "build"], cwd=ROOT / "backend", timeout=180)
    run(state, "migrate-from-zero", ["npm", "run", "db:migrate"], cwd=ROOT / "backend", env={"DATABASE_URL": state.database_url}, timeout=180)
    run(state, "redis-proof", ["npx", "ts-node", probe_arg, "redis"], cwd=ROOT / "backend", env=env, timeout=60)
    wait_until("host KafkaJS health", 60, lambda: run(state, "kafkajs-host-health-proof", ["npx", "ts-node", probe_arg, "kafka-health"], cwd=ROOT / "backend", env=env, timeout=20, allow_failure=True).returncode == 0)

    backend = run_backend_server(state)
    try:
        wait_until("backend health", 45, lambda: http_get(f"http://127.0.0.1:{state.backend_port}/health/live")[0] == 200)
        ready_code, ready_body = http_get(f"http://127.0.0.1:{state.backend_port}/health/ready")
        write_text(state.traces_dir / "backend-readiness.json", ready_body)
        if ready_code != 200:
          raise RuntimeError(f"readiness returned {ready_code}")
        unauthorized, unauthorized_body = http_get(f"http://127.0.0.1:{state.backend_port}/api/agents")
        authorized, authorized_body = http_get(f"http://127.0.0.1:{state.backend_port}/api/agents", {"x-api-key": "runtime-integration-key"})
        write_text(state.traces_dir / "backend-unauthorized.json", unauthorized_body)
        write_text(state.traces_dir / "backend-authorized.json", authorized_body)
        state.workflow_results["http"] = {"live": 200, "ready": ready_code, "unauthorized": unauthorized, "authorized": authorized}
    finally:
        backend.send_signal(signal.SIGTERM)
        collect_process_logs(state, "backend-server", backend)

    correlation = str(uuid.uuid4())
    env = {**env, "RUNTIME_INTEGRATION_CORRELATION_ID": correlation}
    outbox = run(state, "outbox-publish-proof", ["npx", "ts-node", probe_arg, "outbox"], cwd=ROOT / "backend", env=env, timeout=90)
    consume = run(state, "kafka-consume-proof", ["npx", "ts-node", probe_arg, "consume"], cwd=ROOT / "backend", env=env, timeout=90)
    restart = run(state, "outbox-worker-restart-idempotency-proof", ["npx", "ts-node", probe_arg, "restart-check"], cwd=ROOT / "backend", env=env, timeout=90)
    state.workflow_results["outbox"] = json.loads(outbox.stdout.strip().splitlines()[-1])
    state.workflow_results["kafka_consume"] = json.loads(consume.stdout.strip().splitlines()[-1])
    state.workflow_results["restart_recovery"] = json.loads(restart.stdout.strip().splitlines()[-1])

    run(state, "agent-dispatch-e2e", [sys.executable, "-m", "pytest", "agents/tests/integration/test_agent_dispatch_e2e.py", "-q"], env=env, timeout=180)
    run(state, "specialist-spawn-jest", ["npm", "test", "--", "specialist-spawning.test.ts", "--runInBand"], cwd=ROOT / "backend", env=env, timeout=120)

    failed = run(state, "outbox-failure-injection", ["npx", "ts-node", probe_arg, "failure"], cwd=ROOT / "backend", env=env, timeout=90)
    state.workflow_results["failure_injection"] = json.loads(failed.stdout.strip().splitlines()[-1])


def cleanup(state: State) -> None:
    steps: dict[str, Any] = {}
    for command_id, argv in [
        ("cleanup-postgres-logs", ["docker", "logs", state.pg_container]),
        ("cleanup-redis-logs", ["docker", "logs", state.redis_container]),
        ("cleanup-zookeeper-logs", ["docker", "logs", state.zk_container]),
        ("cleanup-kafka-logs", ["docker", "logs", state.kafka_container]),
    ]:
        proc = run(state, command_id, argv, allow_failure=True, timeout=30)
        log_name = command_id.removeprefix("cleanup-").removesuffix("-logs")
        write_text(state.logs_dir / f"{log_name}.stdout.txt", proc.stdout)
        write_text(state.logs_dir / f"{log_name}.stderr.txt", proc.stderr)
    for command_id, argv in [
        ("cleanup-remove-kafka", ["docker", "rm", "-f", state.kafka_container]),
        ("cleanup-remove-zookeeper", ["docker", "rm", "-f", state.zk_container]),
        ("cleanup-remove-redis", ["docker", "rm", "-f", state.redis_container]),
        ("cleanup-remove-postgres", ["docker", "rm", "-f", state.pg_container]),
        ("cleanup-remove-network", ["docker", "network", "rm", state.network]),
        ("cleanup-remove-pg-volume", ["docker", "volume", "rm", state.pg_volume]),
        ("cleanup-remove-redis-volume", ["docker", "volume", "rm", state.redis_volume]),
        ("cleanup-remove-zk-volume", ["docker", "volume", "rm", state.zk_volume]),
        ("cleanup-remove-kafka-volume", ["docker", "volume", "rm", state.kafka_volume]),
    ]:
        proc = run(state, command_id, argv, allow_failure=True, timeout=60)
        steps[command_id] = {"exit_code": proc.returncode, "success": proc.returncode == 0}
    for name, command in [
        (state.pg_container, "container"),
        (state.redis_container, "container"),
        (state.zk_container, "container"),
        (state.kafka_container, "container"),
        (state.pg_volume, "volume"),
        (state.redis_volume, "volume"),
        (state.zk_volume, "volume"),
        (state.kafka_volume, "volume"),
    ]:
        proc = run(state, f"cleanup-verify-{command}-{name}", ["docker", command, "inspect", name], allow_failure=True, timeout=30)
        steps[f"verify-{command}-{name}"] = {"exit_code": proc.returncode, "success": proc.returncode != 0}
    state.cleanup = {"success": all(step["success"] for step in steps.values()), "steps": steps}


def write_ledger(state: State) -> None:
    data = {
        "run_id": state.run_id,
        "commit": state.commit,
        "branch": state.branch,
        "start_time": state.run_id[:15],
        "completed_at": utc(),
        "final_verdict": state.final_verdict,
        "services": {
            "postgres": {"container": state.pg_container, "port": state.pg_port},
            "redis": {"container": state.redis_container, "port": state.redis_port},
            "kafka": {"container": state.kafka_container, "port": state.kafka_port},
            "zookeeper": {"container": state.zk_container},
        },
        "commands": [record.__dict__ for record in state.commands],
        "workflow_results": state.workflow_results,
        "cleanup": state.cleanup,
    }
    (state.artifact_dir / "EXECUTION_LEDGER.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    (state.artifact_dir / "INTEGRATION_SUMMARY.md").write_text(
        f"# Runtime Integration Summary\n\nCommit: `{state.commit}`\n\n"
        f"Run ID: `{state.run_id}`\n\nFinal verdict: `{state.final_verdict}`\n\n"
        f"Commands recorded: `{len(state.commands)}`\n\n"
        f"Cleanup success: `{state.cleanup.get('success')}`\n\n"
        "## Workflow Results\n\n```json\n"
        + json.dumps(state.workflow_results, indent=2, sort_keys=True)
        + "\n```\n"
    )


def main() -> int:
    token = secrets.token_hex(4)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{token}"
    artifact_dir = ARTIFACT_ROOT / run_id
    for sub in ["commands", "process-logs", "http-traces", "database-snapshots", "event-traces", "failure-injection", "test-results", "cleanup-results"]:
        (artifact_dir / sub).mkdir(parents=True, exist_ok=True)
    state = State(
        run_id=run_id,
        commit=git(["rev-parse", "HEAD"]),
        branch=git(["branch", "--show-current"]),
        artifact_dir=artifact_dir,
        command_dir=artifact_dir / "commands",
        logs_dir=artifact_dir / "process-logs",
        traces_dir=artifact_dir / "http-traces",
        cleanup_dir=artifact_dir / "cleanup-results",
        network=f"agentco-rti-{token}",
        pg_container=f"agentco-rti-postgres-{token}",
        redis_container=f"agentco-rti-redis-{token}",
        zk_container=f"agentco-rti-zk-{token}",
        kafka_container=f"agentco-rti-kafka-{token}",
        pg_volume=f"agentco-rti-pg-{token}",
        redis_volume=f"agentco-rti-redis-{token}",
        zk_volume=f"agentco-rti-zk-{token}",
        kafka_volume=f"agentco-rti-kafka-{token}",
        pg_port=available_port(),
        redis_port=available_port(),
        kafka_port=available_port(),
        backend_port=available_port(),
        db_password=secrets.token_urlsafe(18),
    )
    code = 1
    try:
        run(state, "docker-version", ["docker", "--version"])
        start_services(state)
        run_workflows(state)
        state.final_verdict = "PASS"
        code = 0
    except Exception as exc:
        state.workflow_results["fatal_error"] = str(exc)
        print(f"runtime integration failed: {exc}", file=sys.stderr)
    finally:
        try:
            cleanup(state)
        except Exception as exc:
            state.cleanup = {"success": False, "error": str(exc)}
            state.final_verdict = "FAIL"
            code = 1
        if not state.cleanup.get("success"):
            state.final_verdict = "FAIL"
            code = 1
        write_ledger(state)
        print(state.artifact_dir)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
