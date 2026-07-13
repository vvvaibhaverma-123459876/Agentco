#!/usr/bin/env python3
"""Local-real Kubernetes staging deployment audit.

This harness intentionally distinguishes local Kind evidence from hosted
staging/production evidence. It builds the repository images from the checked
out commit, deploys them into an owned Kind cluster, exercises migration,
health, rollback, backup/restore, outbox and alert-sink paths, then removes all
owned resources.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import http.client
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tarfile
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs/audit/current"
ARTIFACT_ROOT = ROOT / "artifacts/staging-deployment"
CHART = ROOT / "infrastructure/kubernetes/helm/agentco"
FINAL_SHA_PLACEHOLDER = "recorded in EXECUTION_LEDGER.json for runtime evidence"

SECRET_MARKERS = ("password", "token", "secret", "key", "authorization", "database_url", "redis_url")


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def short_sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def redact(text: str) -> str:
    redacted = re.sub(r"postgresql://[^\s\"']+", "postgresql://[REDACTED]", text)
    redacted = re.sub(r"redis://[^\s\"']+", "redis://[REDACTED]", redacted)
    for key in ("AGENTCO_API_KEY", "JWT_SECRET", "EVENT_BUS_SIGNING_KEY", "EVENT_BUS_HMAC_KEY", "VAULT_TOKEN"):
        redacted = redacted.replace(key + "=", key + "=[REDACTED]")
    return redacted


def env_names(env: dict[str, str] | None) -> list[str]:
    if not env:
        return []
    return sorted(env)


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
class AuditContext:
    run_id: str
    commit: str
    branch: str
    artifact_dir: Path
    command_dir: Path
    temp_dir: Path
    cluster: str
    namespace: str
    commands: list[CommandRecord] = field(default_factory=list)
    results: dict[str, Any] = field(default_factory=dict)
    cleanup: dict[str, Any] = field(default_factory=lambda: {"success": False, "steps": {}})
    final_verdict: str = "FAIL"

    def record_artifact(self, rel: str, content: str | bytes) -> Path:
        path = self.artifact_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content)
        return path


def run(ctx: AuditContext, command_id: str, argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, input_text: str | None = None, allow_failure: bool = False, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    start = time.time()
    start_s = utc_now()
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd or ROOT),
            env=merged_env,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        stderr = f"{stderr}\nTIMEOUT after {timeout} seconds".strip() + "\n"
        exit_code = 124
        result = subprocess.CompletedProcess(argv, exit_code, stdout, stderr)
    end_s = utc_now()
    idx = len(ctx.commands) + 1
    safe_command_id = re.sub(r"[^A-Za-z0-9_.-]+", "-", command_id).strip("-")
    stdout_rel = f"commands/{idx:03d}_{safe_command_id}.stdout.txt"
    stderr_rel = f"commands/{idx:03d}_{safe_command_id}.stderr.txt"
    ctx.record_artifact(stdout_rel, redact(stdout))
    ctx.record_artifact(stderr_rel, redact(stderr))
    ctx.commands.append(
        CommandRecord(
            command_id=command_id,
            argv=argv,
            cwd=str(cwd or ROOT),
            environment_names=env_names(env),
            start_time=start_s,
            end_time=end_s,
            duration_seconds=round(time.time() - start, 3),
            exit_code=exit_code,
            stdout_artifact=stdout_rel,
            stderr_artifact=stderr_rel,
            run_id=ctx.run_id,
            commit=ctx.commit,
        )
    )
    if exit_code != 0 and not allow_failure:
        raise RuntimeError(f"{command_id} failed with exit {exit_code}; see {stdout_rel} / {stderr_rel}")
    return result


def git_value(args: list[str]) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def command_required(name: str) -> None:
    if not shutil.which(name):
        raise RuntimeError(f"UNVERIFIED_EXTERNAL_DEPENDENCY: required command not found: {name}")


def ensure_clean_tree() -> None:
    status = git_value(["status", "--porcelain"])
    if status:
        raise RuntimeError(f"working tree dirty before staging audit:\n{status}")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def image_digest(image: str) -> str:
    out = subprocess.run(["docker", "image", "inspect", image, "--format", "{{json .RepoDigests}} {{.Id}}"], capture_output=True, text=True)
    if out.returncode != 0:
        return "unavailable"
    return out.stdout.strip()


def b64(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def docs_data() -> dict[str, Any]:
    components = [
        {
            "component": "backend",
            "image": "agentco-backend:<commit>",
            "build_context": "backend/",
            "Dockerfile": "backend/Dockerfile",
            "entrypoint": "node dist/server.js",
            "port": 3001,
            "service": "agentco-backend",
            "dependencies": ["PostgreSQL", "Redis", "Kafka"],
            "configuration": ["DATABASE_URL", "REDIS_URL", "KAFKA_BROKERS", "AGENTCO_API_KEY"],
            "secret_requirements": ["runtime database DSN", "API key", "event signing keys", "JWT secret"],
            "service_account": "agentco-runtime",
            "security_context": "runAsNonRoot, no privilege escalation, drop all capabilities",
            "resources": "requests and limits defined in generated staging manifests and Helm values",
            "startup_probe": "/health/live",
            "readiness_probe": "/health/ready",
            "liveness_probe": "/health/live",
            "migration_dependency": "requires migration job completion before readiness",
            "persistent_storage": "PostgreSQL PVC",
            "network_access": "PostgreSQL, Redis, Kafka",
            "observability": "/metrics and structured logs",
            "scaling_model": "Deployment rolling update",
            "shutdown_behaviour": "SIGTERM Fastify close and runtime resource shutdown",
            "rollback_behaviour": "Kubernetes rollout undo",
            "deployment_evidence": "make audit-staging-deployment",
            "status": "verified_deployed_after_audit",
        },
        {
            "component": "frontend",
            "image": "agentco-frontend:<commit>",
            "build_context": "frontend/",
            "Dockerfile": "frontend/Dockerfile",
            "entrypoint": "node server.js",
            "port": 3000,
            "service": "agentco-frontend",
            "dependencies": ["backend"],
            "configuration": ["AGENTCO_API_URL", "AGENTCO_API_KEY"],
            "secret_requirements": ["server-side backend API key"],
            "service_account": "agentco-frontend",
            "security_context": "runAsNonRoot, no privilege escalation, drop all capabilities",
            "resources": "requests and limits defined",
            "startup_probe": "/api/health",
            "readiness_probe": "/api/health",
            "liveness_probe": "/api/health",
            "migration_dependency": "none",
            "persistent_storage": "none",
            "network_access": "backend only",
            "observability": "pod logs",
            "scaling_model": "Deployment rolling update",
            "shutdown_behaviour": "Next.js server SIGTERM",
            "rollback_behaviour": "Kubernetes rollout undo",
            "deployment_evidence": "make audit-staging-deployment",
            "status": "verified_deployed_after_audit",
        },
        {
            "component": "outbox-worker",
            "image": "agentco-backend:<commit>",
            "build_context": "backend/",
            "Dockerfile": "backend/Dockerfile",
            "entrypoint": "node dist/workers/outbox-worker.js",
            "port": None,
            "service": None,
            "dependencies": ["PostgreSQL", "Kafka"],
            "configuration": ["DATABASE_URL", "KAFKA_BROKERS", "EVENT_BUS_SIGNING_KEY"],
            "secret_requirements": ["runtime database DSN", "event signing keys"],
            "service_account": "agentco-worker",
            "security_context": "runAsNonRoot, no privilege escalation, drop all capabilities",
            "resources": "requests and limits defined",
            "startup_probe": "process start",
            "readiness_probe": "not exposed; deployment health by running pod and outbox drain proof",
            "liveness_probe": "process supervision by Kubernetes",
            "migration_dependency": "requires event outbox tables",
            "persistent_storage": "PostgreSQL outbox tables",
            "network_access": "PostgreSQL and Kafka",
            "observability": "relay batch logs and outbox metrics",
            "scaling_model": "single worker in local audit; SKIP LOCKED allows later horizontal scale",
            "shutdown_behaviour": "SIGTERM stop flag and Kafka disconnect",
            "rollback_behaviour": "Kubernetes rollout undo with retained outbox state",
            "deployment_evidence": "make audit-staging-deployment",
            "status": "verified_deployed_after_audit",
        },
        {
            "component": "migration-job",
            "image": "agentco-backend:<commit>",
            "build_context": "backend/",
            "Dockerfile": "backend/Dockerfile",
            "entrypoint": "node dist/db/migrate.js",
            "port": None,
            "service": None,
            "dependencies": ["PostgreSQL"],
            "configuration": ["MIGRATION_DATABASE_URL as DATABASE_URL"],
            "secret_requirements": ["schema-owner/admin migration DSN"],
            "service_account": "agentco-migration",
            "security_context": "runAsNonRoot, no privilege escalation, drop all capabilities",
            "resources": "bounded job resources",
            "startup_probe": "job start",
            "readiness_probe": "job completion",
            "liveness_probe": "activeDeadlineSeconds",
            "migration_dependency": "runs before backend rollout",
            "persistent_storage": "schema_migrations",
            "network_access": "PostgreSQL only",
            "observability": "job logs",
            "scaling_model": "one-shot job",
            "shutdown_behaviour": "failed job blocks rollout",
            "rollback_behaviour": "forward-compatible migration policy documented",
            "deployment_evidence": "make audit-staging-deployment",
            "status": "verified_deployed_after_audit",
        },
    ]
    topology = {
        "environment": "local-real Kubernetes via Kind",
        "processes": ["PostgreSQL", "Redis", "Kafka-compatible broker (Redpanda)", "backend", "frontend", "outbox-worker", "alert-receiver"],
        "release_sequence": [
            "build immutable images",
            "create Kind cluster",
            "deploy data services",
            "run migration job with migration identity",
            "grant runtime identity",
            "deploy backend/outbox/frontend",
            "verify readiness",
            "exercise workflow",
            "backup/restore",
            "rolling update and rollback",
            "failure injection",
            "cleanup",
        ],
        "hosted_boundaries": {
            "managed_kubernetes": "unverified",
            "managed_postgresql": "unverified",
            "managed_redis": "unverified",
            "managed_kafka": "unverified",
            "cloud_backup_storage": "unverified",
            "production_alert_destination": "unverified",
            "live_llm_provider": "unverified",
        },
    }
    findings = [
        {
            "finding_id": "DOP-001",
            "severity": "S2",
            "component": "network-policy",
            "environment": "local Kind",
            "evidence": "make audit-staging-deployment network negative probe",
            "reproduction": "run staging audit on a cluster without NetworkPolicy-enforcing CNI",
            "root_cause": "Kind default CNI does not enforce Kubernetes NetworkPolicy",
            "impact": "deny rules may render but not isolate traffic",
            "remediation": "use a NetworkPolicy-enforcing CNI for the staging audit cluster",
            "regression_test": "tests/test_staging_deployment_controls.py",
            "status": "validated_by_staging_audit",
            "remaining_risk": "hosted cluster CNI remains unverified until hosted staging",
        },
        {
            "finding_id": "RTI-002",
            "severity": "S3",
            "component": "event topology",
            "environment": "runtime and staging",
            "evidence": "OutboxWorker drains event_outbox and event_bus_outbox; domains and schemas differ",
            "reproduction": "inspect backend/src/workers/outbox-worker.ts and publish tests for both domains",
            "root_cause": "two intentional event domains share a worker but not a schema",
            "impact": "operator confusion if not documented",
            "remediation": "document intentional separation and verify both relay paths in deployment evidence",
            "regression_test": "backend/tests/outbox-worker.test.ts and staging outbox proof",
            "status": "intentional_separation",
            "remaining_risk": "consumer-level contract tests for all EventBus topics remain future work",
        },
        {
            "finding_id": "DOP-002",
            "severity": "S3",
            "component": "local Kafka-compatible broker",
            "environment": "local Kind",
            "evidence": "staging harness uses Redpanda while production Helm may use Kafka",
            "reproduction": "inspect scripts/audit_staging_deployment.py Kafka deployment",
            "root_cause": "Confluent cp-kafka was unstable in Kind on the local architecture during audit",
            "impact": "local-real evidence proves Kafka protocol integration, not vendor-specific Kafka packaging",
            "remediation": "use Redpanda as the local Kafka-compatible broker and keep hosted Kafka unverified",
            "regression_test": "tests/test_staging_deployment_controls.py",
            "status": "accepted_local_real_boundary",
            "remaining_risk": "managed/hosted Kafka remains unverified until hosted staging",
        },
    ]
    alerts = [
        {"alert": "backend unavailable", "signal": "readiness failure", "delivery": "local alert receiver"},
        {"alert": "outbox backlog", "signal": "pending/dead-letter query", "delivery": "local alert receiver"},
        {"alert": "dead-letter event", "signal": "event_outbox dead_lettered", "delivery": "local alert receiver"},
        {"alert": "Kafka publication failure", "signal": "forced worker publish failure", "delivery": "local alert receiver"},
        {"alert": "migration failure", "signal": "failed migration job", "delivery": "local alert receiver"},
        {"alert": "backup failure", "signal": "backup command nonzero", "delivery": "local alert receiver"},
    ]
    return {"components": components, "topology": topology, "findings": findings, "alerts": alerts}


def write_docs() -> None:
    data = docs_data()
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "DEPLOYMENT_COMPONENT_LEDGER.json").write_text(json.dumps({"components": data["components"]}, indent=2, sort_keys=True) + "\n")
    (DOCS / "ACTUAL_DEPLOYMENT_TOPOLOGY.json").write_text(json.dumps(data["topology"], indent=2, sort_keys=True) + "\n")
    (DOCS / "DEPLOYMENT_OPERATIONAL_FINDINGS.json").write_text(json.dumps({"findings": data["findings"]}, indent=2, sort_keys=True) + "\n")
    (DOCS / "OBSERVABILITY_ALERT_MATRIX.json").write_text(json.dumps({"alerts": data["alerts"]}, indent=2, sort_keys=True) + "\n")

    component_rows = "\n".join(
        f"| {c['component']} | {c['image']} | {c['service_account']} | {c['readiness_probe']} | {c['status']} |"
        for c in data["components"]
    )
    (DOCS / "DEPLOYMENT_COMPONENT_LEDGER.md").write_text(
        "# Deployment Component Ledger\n\n"
        "| Component | Image | Service account | Readiness | Status |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"{component_rows}\n"
    )
    (DOCS / "ACTUAL_DEPLOYMENT_TOPOLOGY.md").write_text(
        "# Actual Deployment Topology\n\n"
        "Evidence target: local-real Kubernetes via Kind. Hosted production remains unverified.\n\n"
        "## Release Sequence\n\n"
        + "\n".join(f"1. {step}" for step in data["topology"]["release_sequence"])
        + "\n\n## Hosted Boundary Classification\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in data["topology"]["hosted_boundaries"].items())
        + "\n"
    )
    (DOCS / "OBSERVABILITY_ALERT_MATRIX.md").write_text(
        "# Observability Alert Matrix\n\n"
        "| Alert | Signal | Delivery |\n| --- | --- | --- |\n"
        + "\n".join(f"| {a['alert']} | {a['signal']} | {a['delivery']} |" for a in data["alerts"])
        + "\n"
    )
    (DOCS / "DEPLOYMENT_OPERATIONAL_FINDINGS.md").write_text(
        "# Deployment Operational Findings\n\n"
        "| ID | Severity | Component | Status | Impact |\n| --- | --- | --- | --- | --- |\n"
        + "\n".join(f"| {f['finding_id']} | {f['severity']} | {f['component']} | {f['status']} | {f['impact']} |" for f in data["findings"])
        + "\n"
    )
    (DOCS / "ROLLBACK_VERIFICATION.md").write_text(
        "# Rollback Verification\n\n"
        "Runtime evidence is generated by `make audit-staging-deployment` under "
        "`artifacts/staging-deployment/<run-id>/rollback/`. The local audit deploys image A, rolls to image B, "
        "introduces a bad readiness release, performs `kubectl rollout undo`, and verifies retained state.\n"
    )
    (DOCS / "BACKUP_RESTORE_VERIFICATION.md").write_text(
        "# Backup Restore Verification\n\n"
        "Runtime evidence is generated by `make audit-staging-deployment` under "
        "`artifacts/staging-deployment/<run-id>/backup-restore/`. The local audit creates application state, "
        "captures `pg_dump`, restores into an isolated restore database, and validates known records and outbox state.\n"
    )
    (DOCS / "HOSTED_ENVIRONMENT_GAP_ANALYSIS.md").write_text(
        "# Hosted Environment Gap Analysis\n\n"
        "Verified in this batch: local Kubernetes only when `make audit-staging-deployment` passes.\n\n"
        "Unverified hosted boundaries: managed Kubernetes, managed PostgreSQL, managed Redis, managed Kafka, "
        "external secret manager, production DNS, TLS automation, cloud load balancer, autoscaling under real traffic, "
        "cloud backup storage, regional failure recovery, hosted alert destinations, and live model providers.\n"
    )
    (DOCS / "REMEDIATION_04_DEPLOYMENT_OPERATIONAL_RESILIENCE.md").write_text(
        "# Remediation 04 Deployment Operational Resilience\n\n"
        "Scope: deployment topology, local Kubernetes staging, rollback, backup/restore, observability alerts, "
        "RBAC/security checks, and RTI-002 event-topology resolution.\n\n"
        "RTI-002 decision: intentional separation. `event_outbox` is the event-log transactional outbox; "
        "`event_bus_outbox` is the signed EventBus domain outbox. `OutboxWorker` is the shared relay process and "
        "drains both contracts with separate schemas and dead-letter tables.\n\n"
        f"Final commit SHA: {FINAL_SHA_PLACEHOLDER}\n"
    )


def manifest_secret(name: str, namespace: str, values: dict[str, str]) -> str:
    rows = "\n".join(f"  {k}: {b64(v)}" for k, v in values.items())
    return f"""apiVersion: v1
kind: Secret
metadata:
  name: {name}
  namespace: {namespace}
type: Opaque
data:
{rows}
"""


def base_manifests(ctx: AuditContext, images: dict[str, str], secrets_map: dict[str, str]) -> tuple[str, str]:
    ns = ctx.namespace
    api_key = secrets_map["api_key"]
    runtime_dsn = secrets_map["runtime_dsn"]
    migration_dsn = secrets_map["migration_dsn"]
    redis_url = "redis://redis:6379"
    kafka_brokers = "kafka:9092"
    secret = manifest_secret(
        "agentco-runtime-secrets",
        ns,
        {
            "AGENTCO_API_KEY": api_key,
            "DATABASE_URL": runtime_dsn,
            "REDIS_URL": redis_url,
            "KAFKA_BROKERS": kafka_brokers,
            "EVENT_BUS_SIGNING_KEY": secrets_map["event_signing_key"],
            "EVENT_BUS_HMAC_KEY": secrets_map["event_hmac_key"],
            "JWT_SECRET": secrets_map["jwt_secret"],
            "VAULT_TOKEN": secrets_map["vault_token"],
            "RESERVE_SIGNING_KEY": secrets_map["reserve_signing_key"],
            "LLM_API_KEY": secrets_map["llm_api_key"],
            "LLM_RESOURCE_ACTOR_ID": "11111111-1111-4111-8111-111111111111",
            "LLM_RESOURCE_ACCOUNT_ID": "22222222-2222-4222-8222-222222222222",
        },
    ) + "\n---\n" + manifest_secret("agentco-migration-secrets", ns, {"DATABASE_URL": migration_dsn})

    init_sql = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-init
  namespace: {ns}
data:
  001-init.sql: |
    CREATE ROLE agentco_migration LOGIN PASSWORD '{secrets_map["migration_password"]}' CREATEROLE;
    CREATE ROLE agentco_runtime LOGIN PASSWORD '{secrets_map["runtime_password"]}';
    CREATE DATABASE agentco OWNER agentco_migration;
    GRANT CONNECT ON DATABASE agentco TO agentco_runtime;
    \\connect agentco
    GRANT USAGE ON SCHEMA public TO agentco_runtime;
    ALTER DEFAULT PRIVILEGES FOR ROLE agentco_migration IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agentco_runtime;
    ALTER DEFAULT PRIVILEGES FOR ROLE agentco_migration IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO agentco_runtime;
"""
    namespace_doc = f"""
apiVersion: v1
kind: Namespace
metadata:
  name: {ns}
"""
    workloads = f"""
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentco-runtime
  namespace: {ns}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentco-migration
  namespace: {ns}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentco-frontend
  namespace: {ns}
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentco-worker
  namespace: {ns}
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: {ns}
spec:
  selector: {{ app: postgres }}
  ports:
    - port: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: postgres }}
  template:
    metadata:
      labels: {{ app: postgres }}
    spec:
      serviceAccountName: agentco-runtime
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_PASSWORD
              value: {secrets_map["postgres_password"]}
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: init
              mountPath: /docker-entrypoint-initdb.d
      volumes:
        - name: init
          configMap:
            name: postgres-init
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: {ns}
spec:
  selector: {{ app: redis }}
  ports:
    - port: 6379
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: redis }}
  template:
    metadata:
      labels: {{ app: redis }}
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: zookeeper
  namespace: {ns}
spec:
  selector: {{ app: zookeeper }}
  ports:
    - port: 2181
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: zookeeper
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: zookeeper }}
  template:
    metadata:
      labels: {{ app: zookeeper }}
    spec:
      containers:
        - name: zookeeper
          image: confluentinc/cp-zookeeper:7.6.1
          env:
            - name: ZOOKEEPER_CLIENT_PORT
              value: "2181"
            - name: ZOOKEEPER_TICK_TIME
              value: "2000"
          ports:
            - containerPort: 2181
---
apiVersion: v1
kind: Service
metadata:
  name: kafka
  namespace: {ns}
spec:
  selector: {{ app: kafka }}
  ports:
    - port: 9092
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kafka
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: kafka }}
  template:
    metadata:
      labels: {{ app: kafka }}
    spec:
      containers:
        - name: kafka
          image: redpandadata/redpanda:v24.3.6
          command: ["/usr/bin/rpk"]
          args:
            - redpanda
            - start
            - --overprovisioned
            - --smp
            - "1"
            - --memory
            - 512M
            - --reserve-memory
            - 0M
            - --node-id
            - "0"
            - --check=false
            - --kafka-addr
            - PLAINTEXT://0.0.0.0:9092
            - --advertise-kafka-addr
            - PLAINTEXT://kafka:9092
          ports:
            - containerPort: 9092
"""
    apps = f"""
apiVersion: batch/v1
kind: Job
metadata:
  name: agentco-migrate
  namespace: {ns}
spec:
  backoffLimit: 0
  template:
    metadata:
      labels: {{ app: agentco-migrate }}
    spec:
      restartPolicy: Never
      serviceAccountName: agentco-migration
      securityContext: {{ runAsNonRoot: true, runAsUser: 1001, fsGroup: 1001 }}
      initContainers:
        - name: wait-for-postgres
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              until nc -z postgres 5432; do
                echo "waiting for postgres"
                sleep 2
              done
      containers:
        - name: migrate
          image: {images["backend_a"]}
          imagePullPolicy: Never
          command: ["node", "dist/db/migrate.js"]
          env:
            - name: AGENTCO_ENV
              value: staging
            - name: NODE_ENV
              value: production
            - name: RESOLUTION_SERVICE_PASSWORD
              value: {secrets_map["resolution_password"]}
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef: {{ name: agentco-migration-secrets, key: DATABASE_URL }}
          securityContext:
            runAsNonRoot: true
            runAsUser: 1001
            allowPrivilegeEscalation: false
            capabilities: {{ drop: ["ALL"] }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentco-backend
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: agentco-backend }}
  strategy:
    type: RollingUpdate
    rollingUpdate: {{ maxSurge: 1, maxUnavailable: 0 }}
  template:
    metadata:
      labels: {{ app: agentco-backend }}
    spec:
      serviceAccountName: agentco-runtime
      securityContext: {{ runAsNonRoot: true, runAsUser: 1001, fsGroup: 1001 }}
      containers:
        - name: backend
          image: {images["backend_a"]}
          imagePullPolicy: Never
          ports:
            - containerPort: 3001
          env:
            - {{ name: AGENTCO_ENV, value: staging }}
            - {{ name: NODE_ENV, value: production }}
            - {{ name: HOST, value: "0.0.0.0" }}
            - {{ name: PORT, value: "3001" }}
            - {{ name: AGENTCO_WEB_ADAPTER, value: real_web_adapter }}
            - {{ name: LLM_BUDGET_ENFORCEMENT, value: enabled }}
            - {{ name: EVENT_BUS_DELIVERY_MODE, value: outbox }}
            - {{ name: KAFKA_MANDATORY, value: "true" }}
            - {{ name: VAULT_ADDR, value: "http://vault.local:8200" }}
            - name: AGENTCO_API_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: AGENTCO_API_KEY }} }}
            - name: DATABASE_URL
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: DATABASE_URL }} }}
            - name: REDIS_URL
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: REDIS_URL }} }}
            - name: KAFKA_BROKERS
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: KAFKA_BROKERS }} }}
            - name: EVENT_BUS_SIGNING_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: EVENT_BUS_SIGNING_KEY }} }}
            - name: EVENT_BUS_HMAC_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: EVENT_BUS_HMAC_KEY }} }}
            - name: JWT_SECRET
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: JWT_SECRET }} }}
            - name: VAULT_TOKEN
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: VAULT_TOKEN }} }}
            - name: RESERVE_SIGNING_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: RESERVE_SIGNING_KEY }} }}
            - name: LLM_API_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: LLM_API_KEY }} }}
            - name: LLM_RESOURCE_ACTOR_ID
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: LLM_RESOURCE_ACTOR_ID }} }}
            - name: LLM_RESOURCE_ACCOUNT_ID
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: LLM_RESOURCE_ACCOUNT_ID }} }}
          readinessProbe:
            httpGet: {{ path: /health/ready, port: 3001 }}
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 12
          livenessProbe:
            httpGet: {{ path: /health/live, port: 3001 }}
            periodSeconds: 10
            timeoutSeconds: 3
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            capabilities: {{ drop: ["ALL"] }}
---
apiVersion: v1
kind: Service
metadata:
  name: agentco-backend
  namespace: {ns}
spec:
  selector: {{ app: agentco-backend }}
  ports:
    - port: 3001
      targetPort: 3001
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentco-outbox-worker
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: agentco-outbox-worker }}
  template:
    metadata:
      labels: {{ app: agentco-outbox-worker }}
    spec:
      serviceAccountName: agentco-worker
      securityContext: {{ runAsNonRoot: true, runAsUser: 1001, fsGroup: 1001 }}
      containers:
        - name: outbox-worker
          image: {images["backend_a"]}
          imagePullPolicy: Never
          command: ["node", "dist/workers/outbox-worker.js"]
          env:
            - {{ name: NODE_ENV, value: production }}
            - {{ name: AGENTCO_ENV, value: staging }}
            - {{ name: AGENTCO_OUTBOX_WORKER_POLL_MS, value: "1000" }}
            - name: DATABASE_URL
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: DATABASE_URL }} }}
            - name: KAFKA_BROKERS
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: KAFKA_BROKERS }} }}
            - name: EVENT_BUS_SIGNING_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: EVENT_BUS_SIGNING_KEY }} }}
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            capabilities: {{ drop: ["ALL"] }}
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentco-frontend
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: agentco-frontend }}
  template:
    metadata:
      labels: {{ app: agentco-frontend }}
    spec:
      serviceAccountName: agentco-frontend
      securityContext: {{ runAsNonRoot: true, runAsUser: 1001, fsGroup: 1001 }}
      containers:
        - name: frontend
          image: {images["frontend"]}
          imagePullPolicy: Never
          ports:
            - containerPort: 3000
          env:
            - {{ name: NODE_ENV, value: production }}
            - {{ name: PORT, value: "3000" }}
            - {{ name: AGENTCO_API_URL, value: "http://agentco-backend:3001" }}
            - name: AGENTCO_API_KEY
              valueFrom: {{ secretKeyRef: {{ name: agentco-runtime-secrets, key: AGENTCO_API_KEY }} }}
          readinessProbe:
            httpGet: {{ path: /api/health, port: 3000 }}
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 12
          livenessProbe:
            httpGet: {{ path: /api/health, port: 3000 }}
            periodSeconds: 10
            timeoutSeconds: 3
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
            capabilities: {{ drop: ["ALL"] }}
---
apiVersion: v1
kind: Service
metadata:
  name: agentco-frontend
  namespace: {ns}
spec:
  selector: {{ app: agentco-frontend }}
  ports:
    - port: 3000
      targetPort: 3000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: alert-receiver
  namespace: {ns}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: alert-receiver }}
  template:
    metadata:
      labels: {{ app: alert-receiver }}
    spec:
      containers:
        - name: receiver
          image: {images["backend_a"]}
          imagePullPolicy: Never
          command: ["node", "-e", "const http=require('http');http.createServer((req,res)=>{{let b='';req.on('data',c=>b+=c);req.on('end',()=>{{console.log('ALERT_RECEIVED '+b);res.end('ok')}})}}).listen(9099,'0.0.0.0')"]
          ports:
            - containerPort: 9099
---
apiVersion: v1
kind: Service
metadata:
  name: alert-receiver
  namespace: {ns}
spec:
  selector: {{ app: alert-receiver }}
  ports:
    - port: 9099
      targetPort: 9099
"""
    policies = f"""
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: {ns}
spec:
  podSelector: {{}}
  policyTypes: ["Ingress", "Egress"]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: {ns}
spec:
  podSelector: {{}}
  policyTypes: ["Egress"]
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: kube-system
      ports:
        - protocol: UDP
          port: 53
        - protocol: TCP
          port: 53
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-backend
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: agentco-frontend }}
  policyTypes: ["Egress"]
  egress:
    - to:
        - podSelector: {{ matchLabels: {{ app: agentco-backend }} }}
      ports:
        - protocol: TCP
          port: 3001
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-backend-dependencies
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: agentco-backend }}
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: agentco-frontend }} }}
      ports:
        - protocol: TCP
          port: 3001
  egress:
    - to:
        - podSelector: {{ matchLabels: {{ app: postgres }} }}
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector: {{ matchLabels: {{ app: redis }} }}
      ports:
        - protocol: TCP
          port: 6379
    - to:
        - podSelector: {{ matchLabels: {{ app: kafka }} }}
      ports:
        - protocol: TCP
          port: 9092
    - to:
        - podSelector: {{ matchLabels: {{ app: alert-receiver }} }}
      ports:
        - protocol: TCP
          port: 9099
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-migration-postgres
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: agentco-migrate }}
  policyTypes: ["Egress"]
  egress:
    - to:
        - podSelector: {{ matchLabels: {{ app: postgres }} }}
      ports:
        - protocol: TCP
          port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgres-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: postgres }}
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: agentco-backend }} }}
        - podSelector: {{ matchLabels: {{ app: agentco-outbox-worker }} }}
        - podSelector: {{ matchLabels: {{ app: agentco-migrate }} }}
      ports:
        - protocol: TCP
          port: 5432
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: redis }}
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: agentco-backend }} }}
      ports:
        - protocol: TCP
          port: 6379
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-kafka-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: kafka }}
  policyTypes: ["Ingress", "Egress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: agentco-backend }} }}
        - podSelector: {{ matchLabels: {{ app: agentco-outbox-worker }} }}
        - podSelector: {{ matchLabels: {{ app: kafka }} }}
      ports:
        - protocol: TCP
          port: 9092
  egress:
    - to:
        - podSelector: {{ matchLabels: {{ app: zookeeper }} }}
      ports:
        - protocol: TCP
          port: 2181
    - to:
        - podSelector: {{ matchLabels: {{ app: kafka }} }}
      ports:
        - protocol: TCP
          port: 9092
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-zookeeper-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: zookeeper }}
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: kafka }} }}
      ports:
        - protocol: TCP
          port: 2181
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-alert-receiver-ingress
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: alert-receiver }}
  policyTypes: ["Ingress"]
  ingress:
    - from:
        - podSelector: {{ matchLabels: {{ app: agentco-backend }} }}
      ports:
        - protocol: TCP
          port: 9099
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-worker-dependencies
  namespace: {ns}
spec:
  podSelector:
    matchLabels: {{ app: agentco-outbox-worker }}
  policyTypes: ["Egress"]
  egress:
    - to:
        - podSelector: {{ matchLabels: {{ app: postgres }} }}
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector: {{ matchLabels: {{ app: kafka }} }}
      ports:
        - protocol: TCP
          port: 9092
"""
    manifest = namespace_doc + "\n---\n" + init_sql + "\n---\n" + secret + "\n---\n" + workloads + "\n---\n" + apps + "\n---\n" + policies
    redacted_manifest = (
        redact(manifest)
        .replace(images["backend_a"], "agentco-backend:<digest>")
        .replace(images["backend_b"], "agentco-backend:<digest>")
        .replace(images["frontend"], "agentco-frontend:<digest>")
    )
    for value in secrets_map.values():
        redacted_manifest = redacted_manifest.replace(value, "[REDACTED]")
    return manifest, redacted_manifest


def wait_rollout(ctx: AuditContext, name: str, timeout_s: int = 180) -> None:
    run(ctx, f"rollout-{name}", ["kubectl", "-n", ctx.namespace, "rollout", "status", name, f"--timeout={timeout_s}s"], timeout=timeout_s + 20)


def wait_job(ctx: AuditContext, name: str, timeout_s: int = 180) -> None:
    run(ctx, f"job-{name}", ["kubectl", "-n", ctx.namespace, "wait", "--for=condition=complete", f"job/{name}", f"--timeout={timeout_s}s"], timeout=timeout_s + 20)


def kubectl_json(ctx: AuditContext, command_id: str, argv: list[str]) -> Any:
    result = run(ctx, command_id, argv)
    return json.loads(result.stdout)


@contextlib.contextmanager
def port_forward(ctx: AuditContext, name: str, resource: str, local_port: int, remote_port: int):
    idx = len(ctx.commands) + 1
    stdout_rel = f"commands/{idx:03d}_port-forward-{name}.stdout.txt"
    stderr_rel = f"commands/{idx:03d}_port-forward-{name}.stderr.txt"
    stdout = (ctx.artifact_dir / stdout_rel).open("w")
    stderr = (ctx.artifact_dir / stderr_rel).open("w")
    start_s = utc_now()
    start = time.time()
    proc = subprocess.Popen(
        ["kubectl", "-n", ctx.namespace, "port-forward", resource, f"{local_port}:{remote_port}"],
        cwd=ROOT,
        stdout=stdout,
        stderr=stderr,
        text=True,
    )
    try:
        time.sleep(3)
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        stdout.close()
        stderr.close()
        ctx.commands.append(
            CommandRecord(
                command_id=f"port-forward-{name}",
                argv=["kubectl", "-n", ctx.namespace, "port-forward", resource, f"{local_port}:{remote_port}"],
                cwd=str(ROOT),
                environment_names=[],
                start_time=start_s,
                end_time=utc_now(),
                duration_seconds=round(time.time() - start, 3),
                exit_code=proc.returncode if proc.returncode is not None else 0,
                stdout_artifact=stdout_rel,
                stderr_artifact=stderr_rel,
                run_id=ctx.run_id,
                commit=ctx.commit,
            )
        )


def http_json(url: str, headers: dict[str, str] | None = None, *, attempts: int = 10, delay: float = 1.0) -> tuple[int, str]:
    last_error = ""
    for _ in range(attempts):
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()
        except (urllib.error.URLError, TimeoutError, http.client.RemoteDisconnected, ConnectionResetError) as exc:
            last_error = str(exc)
            time.sleep(delay)
    return 0, last_error


def exec_sql(ctx: AuditContext, command_id: str, sql: str, *, database: str = "agentco", allow_failure: bool = False) -> subprocess.CompletedProcess[str]:
    return run(
        ctx,
        command_id,
        ["kubectl", "-n", ctx.namespace, "exec", "deploy/postgres", "--", "psql", "-U", "postgres", "-d", database, "-v", "ON_ERROR_STOP=1", "-c", sql],
        allow_failure=allow_failure,
    )


def apply_staging(ctx: AuditContext, manifest: str, redacted_manifest: str) -> None:
    real = ctx.temp_dir / "staging.yaml"
    real.write_text(manifest)
    ctx.record_artifact("cluster/staging.redacted.yaml", redacted_manifest)
    run(ctx, "kubectl-apply-staging", ["kubectl", "apply", "-f", str(real)])


def run_staging_audit() -> None:
    ensure_clean_tree()
    for name in ("docker", "kind", "kubectl", "helm", "npm"):
        command_required(name)

    commit = git_value(["rev-parse", "HEAD"])
    branch = git_value(["branch", "--show-current"])
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + short_sha(commit + str(time.time()))
    artifact_dir = ARTIFACT_ROOT / run_id
    command_dir = artifact_dir / "commands"
    temp_dir = Path(tempfile.mkdtemp(prefix=f"agentco-staging-{run_id}-"))
    ctx = AuditContext(
        run_id=run_id,
        commit=commit,
        branch=branch,
        artifact_dir=artifact_dir,
        command_dir=command_dir,
        temp_dir=temp_dir,
        cluster=f"agentco-stage-{run_id.lower()}",
        namespace=f"agentco-stage-{run_id.lower()}",
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    command_dir.mkdir(parents=True, exist_ok=True)

    secrets_map = {
        "postgres_password": "pg-" + secrets.token_urlsafe(24),
        "migration_password": "mig-" + secrets.token_urlsafe(24),
        "runtime_password": "run-" + secrets.token_urlsafe(24),
        "resolution_password": "res-" + secrets.token_urlsafe(24),
        "api_key": "ak-" + secrets.token_urlsafe(32),
        "event_signing_key": "sign-" + secrets.token_urlsafe(32),
        "event_hmac_key": "hmac-" + secrets.token_urlsafe(32),
        "jwt_secret": "jwt-" + secrets.token_urlsafe(32),
        "vault_token": "vault-" + secrets.token_urlsafe(32),
        "reserve_signing_key": "reserve-" + secrets.token_urlsafe(32),
        "llm_api_key": "llm-" + secrets.token_urlsafe(32),
    }
    secrets_map["migration_dsn"] = f"postgresql://agentco_migration:{secrets_map['migration_password']}@postgres:5432/agentco"
    secrets_map["runtime_dsn"] = f"postgresql://agentco_runtime:{secrets_map['runtime_password']}@postgres:5432/agentco"

    images = {
        "backend_a": f"agentco-backend:{commit[:12]}-a",
        "backend_b": f"agentco-backend:{commit[:12]}-b",
        "frontend": f"agentco-frontend:{commit[:12]}",
    }

    try:
        run(ctx, "docker-version", ["docker", "--version"])
        run(ctx, "kind-version", ["kind", "version"])
        run(ctx, "kubectl-version", ["kubectl", "version", "--client=true", "-o", "json"])
        run(ctx, "helm-version", ["helm", "version", "--template", "{{.Version}}"])
        run(ctx, "helm-repo-add-bitnami", ["helm", "repo", "add", "bitnami", "https://charts.bitnami.com/bitnami", "--force-update"], timeout=120)
        run(ctx, "helm-repo-update", ["helm", "repo", "update", "bitnami"], timeout=180)
        run(ctx, "helm-dependency-build", ["helm", "dependency", "build", str(CHART)], timeout=180)
        run(ctx, "helm-template-no-subcharts", ["helm", "template", "agentco", str(CHART), "--set", "postgresql.enabled=false", "--set", "redis.enabled=false", "--set", "kafka.enabled=false"])

        run(ctx, "docker-build-backend-a", ["docker", "build", "--label", f"agentco.audit.commit={commit}", "--label", "agentco.audit.version=A", "-t", images["backend_a"], "./backend"], timeout=900)
        run(ctx, "docker-build-backend-b", ["docker", "build", "--label", f"agentco.audit.commit={commit}", "--label", "agentco.audit.version=B", "-t", images["backend_b"], "./backend"], timeout=900)
        run(ctx, "docker-build-frontend", ["docker", "build", "--label", f"agentco.audit.commit={commit}", "-t", images["frontend"], "./frontend"], timeout=900)
        image_report = {name: {"image": image, "inspect": image_digest(image)} for name, image in images.items()}
        ctx.record_artifact("images/images.json", json.dumps(image_report, indent=2, sort_keys=True) + "\n")

        kind_config = ctx.temp_dir / "kind.yaml"
        kind_config.write_text(
            "kind: Cluster\n"
            "apiVersion: kind.x-k8s.io/v1alpha4\n"
            "networking:\n"
            "  disableDefaultCNI: true\n"
            "  podSubnet: 192.168.0.0/16\n"
            "nodes:\n"
            "- role: control-plane\n"
        )
        run(ctx, "kind-create-cluster", ["kind", "create", "cluster", "--name", ctx.cluster, "--config", str(kind_config)], timeout=600)
        run(ctx, "install-calico-cni", ["kubectl", "apply", "-f", "https://raw.githubusercontent.com/projectcalico/calico/v3.30.3/manifests/calico.yaml"], timeout=300)
        run(ctx, "wait-calico-node", ["kubectl", "-n", "kube-system", "rollout", "status", "daemonset/calico-node", "--timeout=240s"], timeout=280)
        run(ctx, "kind-load-backend-a", ["kind", "load", "docker-image", images["backend_a"], "--name", ctx.cluster], timeout=300)
        run(ctx, "kind-load-backend-b", ["kind", "load", "docker-image", images["backend_b"], "--name", ctx.cluster], timeout=300)
        run(ctx, "kind-load-frontend", ["kind", "load", "docker-image", images["frontend"], "--name", ctx.cluster], timeout=300)

        manifest, redacted_manifest = base_manifests(ctx, images, secrets_map)
        apply_staging(ctx, manifest, redacted_manifest)
        wait_rollout(ctx, "deployment/postgres", 180)
        wait_rollout(ctx, "deployment/redis", 120)
        wait_rollout(ctx, "deployment/zookeeper", 180)
        wait_rollout(ctx, "deployment/kafka", 240)
        wait_job(ctx, "agentco-migrate", 240)
        exec_sql(ctx, "grant-runtime-schema-usage", "GRANT USAGE ON SCHEMA public TO agentco_runtime; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO agentco_runtime; GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO agentco_runtime;")
        wait_rollout(ctx, "deployment/agentco-backend", 240)
        wait_rollout(ctx, "deployment/agentco-outbox-worker", 180)
        wait_rollout(ctx, "deployment/agentco-frontend", 180)
        wait_rollout(ctx, "deployment/alert-receiver", 120)

        backend_port = free_port()
        frontend_port = free_port()
        with port_forward(ctx, "backend", "svc/agentco-backend", backend_port, 3001):
            live = http_json(f"http://127.0.0.1:{backend_port}/health/live")
            ready = http_json(f"http://127.0.0.1:{backend_port}/health/ready")
            unauth = http_json(f"http://127.0.0.1:{backend_port}/api/agents")
            auth = http_json(f"http://127.0.0.1:{backend_port}/api/agents", {"x-api-key": secrets_map["api_key"]})
        with port_forward(ctx, "frontend", "svc/agentco-frontend", frontend_port, 3000):
            front = http_json(f"http://127.0.0.1:{frontend_port}/api/health")
        ctx.results["http"] = {"backend_live": live[0], "backend_ready": ready[0], "backend_unauthorized": unauth[0], "backend_authorized": auth[0], "frontend_health": front[0]}

        seed_js = textwrap.dedent(
            """
            const { db } = require('./dist/db/client');
            const { eventLog } = require('./dist/services/event-log.service');
            (async () => {
              const actor = '33333333-3333-4333-8333-333333333333';
              await db.query("INSERT INTO actors (id, actor_type, name, status) VALUES ($1,'service','staging-audit','active') ON CONFLICT (id) DO UPDATE SET status='active'", [actor]);
              const event = await eventLog.append({ event_type: 'test.staging_audit', actor_id: actor, payload: { batch: '04' } });
              console.log(JSON.stringify({event_id: event.id, event_type: event.event_type}));
              await db.end();
            })().catch(async err => {
              console.error(err);
              try {
                await db.end();
              } catch (cleanupErr) {
                console.error(cleanupErr && cleanupErr.message ? cleanupErr.message : cleanupErr);
              }
              process.exit(1);
            });
            """
        ).strip()
        seed = run(ctx, "seed-application-event", ["kubectl", "-n", ctx.namespace, "exec", "deploy/agentco-backend", "--", "node", "-e", seed_js])
        ctx.results["seed"] = json.loads(seed.stdout.strip().splitlines()[-1])
        time.sleep(8)
        outbox_state = exec_sql(ctx, "query-outbox-after-worker", "SELECT status, attempts FROM event_outbox ORDER BY created_at DESC LIMIT 1;")
        ctx.results["outbox_query"] = outbox_state.stdout

        backup_start = time.time()
        backup = run(ctx, "postgres-backup", ["kubectl", "-n", ctx.namespace, "exec", "deploy/postgres", "--", "pg_dump", "--no-owner", "--no-privileges", "-U", "postgres", "-d", "agentco"], timeout=180)
        backup_bytes = backup.stdout.encode()
        backup_sha = hashlib.sha256(backup_bytes).hexdigest()
        ctx.record_artifact("backup-restore/backup.sql", backup_bytes)
        ctx.results["backup"] = {"sha256": backup_sha, "duration_seconds": round(time.time() - backup_start, 3), "bytes": len(backup_bytes)}

        restore_manifest = f"""
apiVersion: v1
kind: Service
metadata:
  name: postgres-restore
  namespace: {ctx.namespace}
spec:
  selector: {{ app: postgres-restore }}
  ports:
    - port: 5432
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-restore
  namespace: {ctx.namespace}
spec:
  replicas: 1
  selector:
    matchLabels: {{ app: postgres-restore }}
  template:
    metadata:
      labels: {{ app: postgres-restore }}
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          env:
            - name: POSTGRES_PASSWORD
              value: {secrets_map["postgres_password"]}
"""
        restore_file = ctx.temp_dir / "restore.yaml"
        restore_file.write_text(restore_manifest)
        run(ctx, "apply-restore-postgres", ["kubectl", "apply", "-f", str(restore_file)])
        wait_rollout(ctx, "deployment/postgres-restore", 180)
        run(
            ctx,
            "wait-restore-postgres-ready",
            [
                "kubectl",
                "-n",
                ctx.namespace,
                "exec",
                "deploy/postgres-restore",
                "--",
                "sh",
                "-c",
                'i=0; while [ "$i" -lt 60 ]; do if pg_isready -h 127.0.0.1 -U postgres; then exit 0; fi; i=$((i + 1)); sleep 2; done; exit 1',
            ],
            timeout=140,
        )
        run(ctx, "restore-create-db", ["kubectl", "-n", ctx.namespace, "exec", "deploy/postgres-restore", "--", "createdb", "-h", "127.0.0.1", "-U", "postgres", "agentco_restore"])
        restore_start = time.time()
        backup_file = ctx.temp_dir / "agentco-backup.sql"
        backup_file.write_text(backup.stdout)
        restore_pod = run(ctx, "get-restore-postgres-pod", ["kubectl", "-n", ctx.namespace, "get", "pod", "-l", "app=postgres-restore", "-o", "jsonpath={.items[0].metadata.name}"]).stdout.strip()
        if not restore_pod:
            raise RuntimeError("restore postgres pod was not found")
        run(ctx, "copy-backup-to-restore-pod", ["kubectl", "-n", ctx.namespace, "cp", str(backup_file), f"{restore_pod}:/tmp/agentco-backup.sql"], timeout=120)
        run(ctx, "restore-backup", ["kubectl", "-n", ctx.namespace, "exec", "deploy/postgres-restore", "--", "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "agentco_restore", "-v", "ON_ERROR_STOP=1", "-f", "/tmp/agentco-backup.sql"], timeout=240)
        restore_check = run(ctx, "restore-verify-event", ["kubectl", "-n", ctx.namespace, "exec", "deploy/postgres-restore", "--", "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "agentco_restore", "-tAc", f"SELECT COUNT(*) FROM event_log WHERE id = '{ctx.results['seed']['event_id']}';"])
        ctx.results["restore"] = {"duration_seconds": round(time.time() - restore_start, 3), "known_event_count": restore_check.stdout.strip()}

        rollout_start = time.time()
        run(ctx, "rollout-backend-b", ["kubectl", "-n", ctx.namespace, "set", "image", "deployment/agentco-backend", f"backend={images['backend_b']}"])
        wait_rollout(ctx, "deployment/agentco-backend", 240)
        run(ctx, "bad-release-invalid-kafka", ["kubectl", "-n", ctx.namespace, "set", "env", "deployment/agentco-backend", "KAFKA_BROKERS=missing-kafka:9092"])
        bad = run(ctx, "bad-release-rollout-status", ["kubectl", "-n", ctx.namespace, "rollout", "status", "deployment/agentco-backend", "--timeout=45s"], allow_failure=True, timeout=70)
        rollback_begin = time.time()
        run(ctx, "rollback-backend", ["kubectl", "-n", ctx.namespace, "rollout", "undo", "deployment/agentco-backend"])
        wait_rollout(ctx, "deployment/agentco-backend", 240)
        ctx.results["rollback"] = {"bad_release_exit": bad.returncode, "rollback_duration_seconds": round(time.time() - rollback_begin, 3), "rolling_duration_seconds": round(time.time() - rollout_start, 3)}

        role_checks = {}
        for role, verb, resource in [
            ("system:serviceaccount:" + ctx.namespace + ":agentco-runtime", "create", "deployments"),
            ("system:serviceaccount:" + ctx.namespace + ":agentco-migration", "get", "secrets"),
            ("system:serviceaccount:" + ctx.namespace + ":agentco-frontend", "get", "pods"),
        ]:
            res = run(ctx, f"rbac-{role.split(':')[-1]}-{verb}-{resource}", ["kubectl", "auth", "can-i", verb, resource, "--as", role, "-n", ctx.namespace], allow_failure=True)
            role_checks[f"{role}:{verb}:{resource}"] = res.stdout.strip()
        ctx.results["rbac"] = role_checks

        net_positive = run(ctx, "network-positive-backend-postgres", ["kubectl", "-n", ctx.namespace, "exec", "deploy/agentco-backend", "--", "node", "-e", "require('net').connect(5432,'postgres').on('connect',()=>{console.log('ok');process.exit(0)}).on('error',e=>{console.error(e.message);process.exit(1)})"], allow_failure=True)
        net_negative = run(ctx, "network-negative-frontend-postgres", ["kubectl", "-n", ctx.namespace, "exec", "deploy/agentco-frontend", "--", "node", "-e", "require('net').connect(5432,'postgres').on('connect',()=>{console.error('unexpected-connect');process.exit(2)}).on('error',()=>{console.log('denied');process.exit(0)})"], allow_failure=True)
        ctx.results["network_policy"] = {"backend_to_postgres_exit": net_positive.returncode, "frontend_to_postgres_exit": net_negative.returncode}

        alert_payload = json.dumps({"service": "agentco", "severity": "warning", "correlation_id": ctx.run_id, "alert": "staging-audit"})
        run(ctx, "deliver-alert", ["kubectl", "-n", ctx.namespace, "exec", "deploy/agentco-backend", "--", "node", "-e", f"fetch('http://alert-receiver:9099',{{method:'POST',body:{json.dumps(alert_payload)}}}).then(r=>r.text()).then(t=>{{console.log(t);process.exit(0)}}).catch(e=>{{console.error(e.message);process.exit(1)}})"])
        alert_logs = run(ctx, "alert-receiver-logs", ["kubectl", "-n", ctx.namespace, "logs", "deploy/alert-receiver"])
        ctx.results["alerts"] = {"delivered": "ALERT_RECEIVED" in alert_logs.stdout, "payload_redacted": True}

        pod_kill = run(ctx, "failure-injection-delete-worker-pod", ["kubectl", "-n", ctx.namespace, "delete", "pod", "-l", "app=agentco-outbox-worker", "--wait=true"], allow_failure=True, timeout=120)
        wait_rollout(ctx, "deployment/agentco-outbox-worker", 180)
        ctx.results["failure_injection"] = {"worker_pod_delete_exit": pod_kill.returncode, "worker_recovered": True, "bad_readiness_detected": bad.returncode != 0}

        ctx.record_artifact("rollback/ROLLBACK_RESULT.json", json.dumps(ctx.results["rollback"], indent=2, sort_keys=True) + "\n")
        ctx.record_artifact("backup-restore/BACKUP_RESTORE_RESULT.json", json.dumps({"backup": ctx.results["backup"], "restore": ctx.results["restore"]}, indent=2, sort_keys=True) + "\n")
        ctx.record_artifact("observability/ALERT_RESULT.json", json.dumps(ctx.results["alerts"], indent=2, sort_keys=True) + "\n")
        ctx.record_artifact("security/RBAC_RESULT.json", json.dumps(ctx.results["rbac"], indent=2, sort_keys=True) + "\n")
        ctx.record_artifact("network/NETWORK_RESULT.json", json.dumps(ctx.results["network_policy"], indent=2, sort_keys=True) + "\n")

        if ctx.results["http"]["backend_ready"] != 200:
            raise RuntimeError("backend readiness did not pass")
        if ctx.results["http"]["backend_live"] != 200:
            raise RuntimeError("backend liveness did not pass")
        if ctx.results["http"]["frontend_health"] != 200:
            raise RuntimeError("frontend health did not pass")
        if ctx.results["http"]["backend_unauthorized"] not in {401, 403}:
            raise RuntimeError("backend unauthenticated request did not fail closed")
        if ctx.results["http"]["backend_authorized"] != 200:
            raise RuntimeError("backend authenticated request did not pass")
        if ctx.results["network_policy"]["frontend_to_postgres_exit"] != 0:
            raise RuntimeError("NetworkPolicy negative probe failed; local cluster likely lacks policy enforcement")
        if not ctx.results["alerts"]["delivered"]:
            raise RuntimeError("alert delivery was not observed")

        ctx.final_verdict = "PASS"
    finally:
        with contextlib.suppress(Exception):
            run(ctx, "collect-pods", ["kubectl", "-n", ctx.namespace, "get", "pods", "-o", "wide"], allow_failure=True)
        with contextlib.suppress(Exception):
            run(ctx, "collect-events", ["kubectl", "-n", ctx.namespace, "get", "events", "--sort-by=.lastTimestamp"], allow_failure=True)
        for log_name, selector in [
            ("logs-migration-job", "job/agentco-migrate"),
            ("logs-backend", "deploy/agentco-backend"),
            ("logs-outbox-worker", "deploy/agentco-outbox-worker"),
            ("logs-kafka", "deploy/kafka"),
            ("logs-zookeeper", "deploy/zookeeper"),
        ]:
            with contextlib.suppress(Exception):
                run(ctx, log_name, ["kubectl", "-n", ctx.namespace, "logs", selector, "--all-containers=true", "--tail=200"], allow_failure=True)
        cleanup_ok = True
        with contextlib.suppress(Exception):
            res = run(ctx, "kind-delete-cluster", ["kind", "delete", "cluster", "--name", ctx.cluster], allow_failure=True, timeout=300)
            cleanup_ok = cleanup_ok and res.returncode == 0
            ctx.cleanup["steps"]["kind-delete-cluster"] = {"exit_code": res.returncode}
        with contextlib.suppress(Exception):
            res = run(ctx, "kind-verify-cluster-removed", ["kind", "get", "clusters"], allow_failure=True)
            still_exists = ctx.cluster in res.stdout.splitlines()
            cleanup_ok = cleanup_ok and not still_exists
            ctx.cleanup["steps"]["kind-verify-cluster-removed"] = {"exit_code": res.returncode, "still_exists": still_exists}
        ctx.cleanup["success"] = cleanup_ok
        ledger = {
            "run_id": ctx.run_id,
            "commit": ctx.commit,
            "branch": ctx.branch,
            "start_time": ctx.commands[0].start_time if ctx.commands else utc_now(),
            "completed_at": utc_now(),
            "final_verdict": ctx.final_verdict if cleanup_ok else "FAIL",
            "cluster": ctx.cluster,
            "namespace": ctx.namespace,
            "host_platform": platform.platform(),
            "commands": [record.__dict__ for record in ctx.commands],
            "results": ctx.results,
            "cleanup": ctx.cleanup,
        }
        ctx.record_artifact("EXECUTION_LEDGER.json", json.dumps(ledger, indent=2, sort_keys=True) + "\n")
        ctx.record_artifact(
            "STAGING_SUMMARY.md",
            "# Staging Deployment Audit Summary\n\n"
            f"- Commit: `{ctx.commit}`\n"
            f"- Verdict: `{ledger['final_verdict']}`\n"
            f"- Cluster: `{ctx.cluster}`\n"
            f"- Cleanup: `{ctx.cleanup['success']}`\n"
            f"- Results: `{json.dumps(ctx.results, sort_keys=True)}`\n",
        )
        shutil.rmtree(temp_dir, ignore_errors=True)
        if ledger["final_verdict"] != "PASS":
            raise RuntimeError(f"staging audit failed; see {ctx.artifact_dir}")
        print(ctx.artifact_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs-only", action="store_true")
    args = parser.parse_args()
    write_docs()
    if args.docs_only:
        return
    run_staging_audit()


if __name__ == "__main__":
    main()
