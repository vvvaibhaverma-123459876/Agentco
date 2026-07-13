#!/usr/bin/env python3
"""Generate Batch 03 runtime architecture evidence snapshots.

This is intentionally conservative: it records what is statically reachable
from active entry points and labels unexecuted/experimental paths as such. It
does not assign production readiness.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "audit" / "current"


@dataclass
class Component:
    component_id: str
    name: str
    path: str
    language: str
    classification: str
    purpose: str
    authoritative_status: str
    entrypoint: str | None
    process_type: str
    startup_command: str | None
    direct_callers: list[str]
    direct_dependencies: list[str]
    external_dependencies: list[str]
    configuration: list[str]
    state_read: list[str]
    state_written: list[str]
    database_tables: list[str]
    events_produced: list[str]
    events_consumed: list[str]
    authentication_boundary: str
    authorization_boundary: str
    budget_boundary: str
    audit_boundary: str
    failure_behaviour: str
    retry_behaviour: str
    idempotency_mechanism: str
    tests: list[str]
    runtime_evidence: list[str]
    deployment_reference: list[str]
    known_findings: list[str]
    review_commit: str


@dataclass
class EntryPoint:
    entry_point: str
    registration_location: str
    authentication_requirement: str
    authorization_requirement: str
    first_handler: str
    service_chain: list[str]
    persistence_effects: list[str]
    events_emitted: list[str]
    outbound_calls: list[str]
    terminal_output: str
    tests: list[str]
    runtime_trace: str
    status: str


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def structural_snapshot_id() -> str:
    roots = ["backend/src", "agents/autonomy", "runtime", "learning", "synthesis", "evals/enterprise_vendor_risk"]
    digest = hashlib.sha256()
    for root in roots:
        for path in sorted((ROOT / root).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix not in {".ts", ".py", ".json", ".sql"}:
                continue
            digest.update(str(path.relative_to(ROOT)).encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def read(path: Path) -> str:
    return path.read_text(errors="replace")


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def rg(pattern: str, *paths: str) -> list[str]:
    cmd = ["rg", "-n", pattern, *paths]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr)
    return proc.stdout.splitlines()


def ts_imports(path: Path) -> list[str]:
    deps: list[str] = []
    for line in read(path).splitlines():
        match = re.search(r"from ['\"]([^'\"]+)['\"]", line) or re.search(r"require\(['\"]([^'\"]+)['\"]\)", line)
        if match:
            deps.append(match.group(1))
    return sorted(set(deps))


def py_imports(path: Path) -> list[str]:
    deps: list[str] = []
    try:
        tree = ast.parse(read(path))
    except SyntaxError:
        return deps
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            deps.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            deps.append(node.module)
    return sorted(set(deps))


def tables_in(path: Path) -> list[str]:
    text = read(path)
    names = set(re.findall(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)", text, flags=re.I))
    return sorted(name for name in names if name.lower() not in {"if", "where", "set", "values"})


def envs_in(path: Path) -> list[str]:
    text = read(path)
    return sorted(set(re.findall(r"process\.env\.([A-Z0-9_]+)|os\.environ\.get\(['\"]([A-Z0-9_]+)['\"]", text)))


def flatten_envs(values: Iterable[tuple[str, str] | str]) -> list[str]:
    out: set[str] = set()
    for value in values:
        if isinstance(value, tuple):
            out.update(v for v in value if v)
        elif value:
            out.add(value)
    return sorted(out)


def component_for(path: Path, head: str) -> Component:
    text = read(path)
    language = "typescript" if path.suffix == ".ts" else "python" if path.suffix == ".py" else path.suffix.lstrip(".")
    deps = ts_imports(path) if language == "typescript" else py_imports(path) if language == "python" else []
    path_s = rel(path)

    classification = "runtime_support"
    authoritative = "support"
    process_type = "library"
    startup: str | None = None
    entry: str | None = None

    if path_s == "backend/src/server.ts":
        classification = "authoritative_runtime"
        authoritative = "authoritative"
        process_type = "backend_http_server"
        startup = "cd backend && npm start"
        entry = "node dist/server.js"
    elif path_s == "backend/src/workers/outbox-worker.ts":
        classification = "authoritative_runtime"
        authoritative = "authoritative"
        process_type = "worker"
        startup = "cd backend && npm run agentco:outbox-worker"
        entry = "npm run agentco:outbox-worker"
    elif path_s.startswith("backend/src/routes/"):
        classification = "authoritative_runtime"
        authoritative = "authoritative"
        process_type = "http_route_module"
        entry = "backend/src/server.ts route registration"
    elif path_s.startswith("backend/src/services/"):
        process_type = "service"
    elif path_s.startswith("backend/src/db/"):
        process_type = "database_runtime"
    elif path_s.startswith("agents/autonomy/"):
        classification = "authoritative_runtime" if "__main__" in text or "SpecialistAgent" in text else "runtime_support"
        authoritative = "live_specialist_runtime" if "SpecialistAgent" in text or path.name == "__main__.py" else "support"
        process_type = "python_specialist_agent"
        entry = "python3.13 -m agents.autonomy.<role>"
        startup = "spawned by backend TeamActivationService"
    elif path_s.startswith("runtime/"):
        classification = "authoritative_runtime" if "base_agent_v2" in path_s or "controlled_learning" in path_s or "self_improvement" in path_s else "runtime_support"
        authoritative = "authoritative" if classification == "authoritative_runtime" else "support"
        process_type = "python_governance_runtime"
    elif path_s.startswith("learning/") or path_s.startswith("synthesis/"):
        classification = "experimental"
        authoritative = "experimental"
        process_type = "python_research_module"
    elif path_s.startswith("evals/"):
        classification = "runtime_support"
        authoritative = "benchmark_support"
        process_type = "evaluation_support"

    if ".disabled" in path_s or "unsupported_migrations" in path_s:
        classification = "historical"
        authoritative = "not_authoritative"

    auth = "protected by backend preHandler unless route config public" if path_s.startswith("backend/src/routes/") or path_s == "backend/src/server.ts" else "not_applicable"
    budget = "resource-ledger/runtime spend controls" if "budget" in text.lower() or "resource" in path_s else "not_applicable"
    audit = "decision_log/event_log/audit writer" if any(word in text for word in ("decision_log", "Audit", "auditLog", "EventLogService")) else "not_applicable"
    external = []
    if "Kafka" in text or "kafka" in text:
        external.append("Kafka")
    if "Redis" in text or "ioredis" in text:
        external.append("Redis")
    if "pg" in text or "db.query" in text or "DATABASE_URL" in text:
        external.append("PostgreSQL")
    if "openai" in text.lower() or "LLM" in text:
        external.append("LLM provider")

    tests = [line.split(":", 1)[0] for line in rg(re.escape(path.name), "tests", "backend/tests", "agents/tests", "runtime/tests")][:12]

    return Component(
        component_id=re.sub(r"[^a-z0-9]+", "-", path_s.lower()).strip("-"),
        name=path.stem,
        path=path_s,
        language=language,
        classification=classification,
        purpose=(text.splitlines()[0].strip("/*# ") if text.splitlines() else "runtime file"),
        authoritative_status=authoritative,
        entrypoint=entry,
        process_type=process_type,
        startup_command=startup,
        direct_callers=[],
        direct_dependencies=deps[:25],
        external_dependencies=sorted(set(external)),
        configuration=flatten_envs(envs_in(path)),
        state_read=tables_in(path),
        state_written=tables_in(path),
        database_tables=tables_in(path),
        events_produced=sorted(set(re.findall(r"event_type[:=]\s*['\"]([^'\"]+)", text))),
        events_consumed=sorted(set(re.findall(r"consume\(['\"]([^'\"]+)", text))),
        authentication_boundary=auth,
        authorization_boundary="route auth/RBAC/tool allowlist where invoked" if "auth" in text.lower() or "permission" in text.lower() else "not_observed",
        budget_boundary=budget,
        audit_boundary=audit,
        failure_behaviour="throws or returns non-2xx; see runtime tests" if "throw" in text or "reply.status" in text else "not_observed",
        retry_behaviour="bounded retry/outbox" if "retry" in text.lower() or "attempt" in text.lower() else "not_observed",
        idempotency_mechanism="idempotency key/ON CONFLICT" if "idempot" in text.lower() or "ON CONFLICT" in text else "not_observed",
        tests=sorted(set(tests)),
        runtime_evidence=["make audit-runtime-integration"] if classification == "authoritative_runtime" else [],
        deployment_reference=["backend/Dockerfile", "docker-compose.yml"] if path_s.startswith("backend/") else [],
        known_findings=[],
        review_commit=head,
    )


def discover_components(head: str) -> list[Component]:
    roots = ["backend/src", "agents/autonomy", "runtime", "learning", "synthesis", "evals/enterprise_vendor_risk"]
    paths: list[Path] = []
    for root in roots:
        paths.extend((ROOT / root).rglob("*.ts"))
        paths.extend((ROOT / root).rglob("*.py"))
    return [component_for(path, head) for path in sorted(set(paths)) if "__pycache__" not in path.parts]


def discover_entrypoints() -> list[EntryPoint]:
    entries: list[EntryPoint] = []
    server = ROOT / "backend/src/server.ts"
    text = read(server)
    for match in re.finditer(r"app\.register\((\w+)\)", text):
        route_name = match.group(1)
        entries.append(EntryPoint(
            entry_point=f"Fastify route module {route_name}",
            registration_location=f"backend/src/server.ts:{text[:match.start()].count(chr(10)) + 1}",
            authentication_requirement="default protected unless route config public",
            authorization_requirement="route/service specific",
            first_handler=route_name,
            service_chain=[],
            persistence_effects=[],
            events_emitted=[],
            outbound_calls=[],
            terminal_output="HTTP response",
            tests=[],
            runtime_trace="make audit-runtime-integration",
            status="verified_static_registration",
        ))
    for route_file in sorted((ROOT / "backend/src/routes").glob("*.ts")):
        route_text = read(route_file)
        for match in re.finditer(r"\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)", route_text):
            entries.append(EntryPoint(
                entry_point=f"{match.group(1).upper()} {match.group(2)}",
                registration_location=f"{rel(route_file)}:{route_text[:match.start()].count(chr(10)) + 1}",
                authentication_requirement="protected unless explicitly public",
                authorization_requirement="handler/service specific",
                first_handler=rel(route_file),
                service_chain=sorted(set(re.findall(r"(\w+Service)\.", route_text))),
                persistence_effects=tables_in(route_file),
                events_emitted=sorted(set(re.findall(r"event_type[:=]\s*['\"]([^'\"]+)", route_text))),
                outbound_calls=[],
                terminal_output="HTTP response",
                tests=[line.split(":", 1)[0] for line in rg(re.escape(route_file.stem), "backend/tests")][:8],
                runtime_trace="make audit-runtime-integration for health/agents/outbox paths",
                status="verified_static_route",
            ))
    entries.extend([
        EntryPoint("CLI backend outbox worker", "backend/package.json:scripts.agentco:outbox-worker", "process env", "not_applicable", "backend/src/workers/outbox-worker.ts", ["TransactionalOutboxService", "EventBusService"], ["event_outbox", "event_bus_outbox"], ["Kafka"], [], "console/exit code", ["backend/tests"], "make audit-runtime-integration", "verified_local_real"),
        EntryPoint("Python specialist subprocess", "backend/src/services/team-activation.service.ts:spawnSpecialistProcess", "parent backend request", "specialist role registry", "agents.autonomy.<role>", ["SpecialistAgent"], ["autonomy_team_activations", "autonomy_evidence"], [], ["HTTP loopback"], "HTTP JSON", ["backend/tests/specialist-spawning.test.ts", "agents/tests/test_specialist_server_runtime.py"], "make audit-runtime-integration", "verified_local_real"),
    ])
    return entries


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_markdown(path: Path, title: str, rows: list[dict[str, object]], columns: list[str]) -> None:
    lines = [f"# {title}", "", f"Tracked structural snapshot input hash `{structural_snapshot_id()}`.", ""]
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("\n", " ")[:500] for col in columns) + " |")
    lines.append("")
    path.write_text("\n".join(lines))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = structural_snapshot_id()
    snapshot_ref = f"tracked_structural_snapshot:{snapshot}"
    components = [asdict(c) for c in discover_components(snapshot_ref)]
    entries = [asdict(e) for e in discover_entrypoints()]

    write_json(OUT / "RUNTIME_COMPONENT_LEDGER.json", {"source_input_hash": snapshot, "components": components})
    write_markdown(
        OUT / "RUNTIME_COMPONENT_LEDGER.md",
        "Runtime Component Ledger",
        components,
        ["component_id", "path", "classification", "authoritative_status", "process_type", "entrypoint", "external_dependencies"],
    )

    write_json(OUT / "RUNTIME_REACHABILITY.json", {"source_input_hash": snapshot, "entrypoints": entries})
    write_markdown(
        OUT / "RUNTIME_REACHABILITY.md",
        "Runtime Reachability",
        entries,
        ["entry_point", "registration_location", "first_handler", "status", "runtime_trace"],
    )

    architecture = {
        "source_input_hash": snapshot,
        "process_topology": [
            {"path": "frontend -> backend", "status": "configured_unexecuted_in_batch"},
            {"path": "backend Fastify -> PostgreSQL", "status": "verified_local_real"},
            {"path": "backend EventLogService -> event_outbox -> outbox worker -> Kafka", "status": "verified_local_real"},
            {"path": "backend TeamActivationService -> python3.13 -m agents.autonomy.<role>", "status": "verified_local_real"},
            {"path": "Python BaseAgentV2 -> durable audit writer -> decision_log", "status": "verified_local_real via release/clean-room tests"},
        ],
        "claimed_vs_executable": [
            {"claim": "all active agents governed", "executable_status": "verified by agent protocol matrix and release gate"},
            {"claim": "bounded learning/self-improvement", "executable_status": "mechanisms tested locally; no autonomous production mutation proof claimed"},
            {"claim": "Kafka-backed eventing", "executable_status": "event_log transactional outbox verified; event_bus outbox classified as parallel active implementation"},
        ],
    }
    write_json(OUT / "ACTUAL_RUNTIME_ARCHITECTURE.json", architecture)
    (OUT / "ACTUAL_RUNTIME_ARCHITECTURE.md").write_text(
        "# Actual Runtime Architecture\n\n"
        f"Tracked structural snapshot input hash `{snapshot}`.\n\n"
        "## Process Topology\n\n"
        "- Verified active path: backend Fastify, PostgreSQL, Redis probe, Kafka, outbox worker, Python specialist subprocess.\n"
        "- Configured but unexecuted path: browser-to-frontend proxy full UI path in this batch.\n"
        "- Experimental path: standalone `learning/` and `synthesis/` modules not wired into deployed backend process.\n"
        "- Historical path: `.disabled` routes and unsupported migrations.\n\n"
        "## HTTP Request Topology\n\n"
        "`backend/src/server.ts` registers route modules under default API-key protection, with public health probes.\n\n"
        "## Agent Execution Topology\n\n"
        "Active TS backend dispatch can spawn Python specialists through `TeamActivationService` using `python3.13 -m agents.autonomy.${role}`.\n\n"
        "## Data Persistence Topology\n\n"
        "PostgreSQL is authoritative for migrations, decision logs, event logs, resource ledgers, evidence, agent tasks, and runtime governance artifacts.\n\n"
        "## Event And Outbox Topology\n\n"
        "`EventLogService.appendWithClient()` writes `event_log` and `event_outbox` in one transaction. `OutboxWorker` relays to Kafka. `EventBusService` also owns an `event_bus_outbox`; this is a parallel active implementation and is recorded in `AUTHORITATIVE_IMPLEMENTATIONS.md`.\n\n"
        "## Governance And Audit Topology\n\n"
        "Python BaseAgentV2 uses audit writer and evidence capture; backend uses decision/event logs and route auth.\n\n"
        "## Learning And Promotion Topology\n\n"
        "Runtime packages implement evaluation, controlled learning, and self-improvement guards. Batch 03 treats long-horizon learning as unproven.\n\n"
        "## Authentication And Authorization Topology\n\n"
        "Backend default route auth is enforced in `server.ts`; tool and agent authorization are enforced by runtime protocol tests.\n\n"
        "## Failure And Recovery Topology\n\n"
        "Outbox rows remain pending/failed/dead-lettered with bounded attempts; restart recovery is checked by rerunning the outbox worker against retained rows.\n\n"
        "## Deployment Topology\n\n"
        "Local Docker Compose and CI workflows are configured. Hosted Kubernetes deployment is not proven in this batch.\n\n"
        "## Claimed Architecture Versus Executable Architecture\n\n"
        "The executable architecture is a supervised, evidence-governed local runtime. General intelligence, hosted production, and longitudinal improvement claims remain outside this batch.\n"
    )

    concepts = [
        ("Agents", "Python BaseAgentV2 active agents and TS TeamActivation specialist spawner", "authoritative", "release gate, specialist spawn tests, runtime integration"),
        ("V1 specialists", "agents/autonomy SpecialistAgent subclasses", "compatibility layer", "live only through TS spawner; high/critical V1 governance remains blocked"),
        ("Audit writers", "Python DurableAuditWriter + TS audit/event log services", "authoritative with cross-writer contract", "decision_log chain tests and runtime outbox proof"),
        ("Event publication", "EventLogService transactional outbox", "authoritative for transactional event_log outbox", "make audit-runtime-integration"),
        ("EventBus outbox", "EventBusService event_bus_outbox", "parallel active implementation", "candidate for consolidation with event_log outbox"),
        ("Learning", "runtime/controlled_learning and runtime/self_improvement", "authoritative bounded mechanisms", "release gate report checks; no longitudinal mission proof"),
        ("Standalone learning/ synthesis", "learning/ and synthesis/", "experimental", "tests only; no backend deployment startup wiring observed"),
    ]
    (OUT / "AUTHORITATIVE_IMPLEMENTATIONS.md").write_text(
        "# Authoritative Implementations\n\n"
        f"Tracked structural snapshot input hash: `{snapshot}`\n\n"
        "| Concept | Implementation | Decision | Evidence |\n| --- | --- | --- | --- |\n"
        + "\n".join(f"| {a} | {b} | {c} | {d} |" for a, b, c, d in concepts)
        + "\n\nConsolidation recommendation: keep the event-log transactional outbox as the authoritative durable event path and either adapt or retire `event_bus_outbox` after a compatibility plan.\n"
    )

    contracts = [
        ("frontend", "backend", "HTTP", "configured_unexecuted", "frontend typecheck/build; no browser E2E in Batch 03"),
        ("backend", "PostgreSQL", "pg", "verified_local_real", "migrations + runtime integration"),
        ("backend", "Redis", "ioredis", "verified_local_real", "runtime integration ping/set/get"),
        ("event_log transaction", "event_outbox", "PostgreSQL transaction", "verified_local_real", "runtime integration"),
        ("outbox worker", "Kafka", "KafkaJS", "verified_local_real", "runtime integration"),
        ("Kafka", "consumer", "KafkaJS", "verified_local_real", "runtime integration consumer read"),
        ("agent", "tool registry", "Python runtime", "verified_local_real", "release/clean-room agent tests"),
        ("evaluation", "learning proposal", "Python runtime", "integration_tested", "release gate report checks"),
    ]
    matrix = [{"producer": a, "consumer": b, "transport": c, "status": d, "runtime_test": e} for a, b, c, d, e in contracts]
    write_json(OUT / "INTEGRATION_CONTRACT_MATRIX.json", {"source_input_hash": snapshot, "contracts": matrix})
    write_markdown(OUT / "INTEGRATION_CONTRACT_MATRIX.md", "Integration Contract Matrix", matrix, ["producer", "consumer", "transport", "status", "runtime_test"])

    findings = [
        {
            "finding_id": "RTI-001",
            "severity": "S2",
            "component": "CI",
            "workflow": "general CI",
            "evidence": "CI run 29238640790 used divergent commands and PR merge checkout.",
            "root_cause": "CI duplicated release checks instead of invoking canonical governed commands.",
            "status": "resolved_in_batch",
            "remaining_risk": "Hosted production remains unverified.",
        },
        {
            "finding_id": "RTI-002",
            "severity": "S3",
            "component": "eventing",
            "workflow": "outbox",
            "evidence": "Both event_outbox and event_bus_outbox exist as active relay paths.",
            "root_cause": "Parallel event mechanisms introduced across phases.",
            "status": "backlog",
            "remaining_risk": "Operational complexity until one path is consolidated.",
        },
    ]
    write_json(OUT / "RUNTIME_INTEGRATION_FINDINGS.json", {"source_input_hash": snapshot, "findings": findings})
    write_markdown(OUT / "RUNTIME_INTEGRATION_FINDINGS.md", "Runtime Integration Findings", findings, ["finding_id", "severity", "component", "workflow", "status", "remaining_risk"])

    claims = [
        {"claim": "Clean-room verification is isolated and fail-closed", "evidence_level": "local_real", "status": "verified", "evidence": "make audit-clean-room and GHA artifact from Batch 02B"},
        {"claim": "Runtime eventing uses Kafka", "evidence_level": "local_real", "status": "verified_with_limitations", "evidence": "make audit-runtime-integration event_outbox path"},
        {"claim": "Active agents use governed protocol", "evidence_level": "integration_tested", "status": "verified", "evidence": "agent protocol matrix and release gate"},
        {"claim": "General intelligence / civilization learns continuously", "evidence_level": "static_contract", "status": "unverified", "evidence": "mechanisms exist; longitudinal proof not in scope"},
    ]
    write_json(OUT / "CLAIM_EVIDENCE_MATRIX.json", {"source_input_hash": snapshot, "claims": claims})
    write_markdown(OUT / "CLAIM_EVIDENCE_MATRIX.md", "Claim Evidence Matrix", claims, ["claim", "evidence_level", "status", "evidence"])

    coverage = {
        "source_input_hash": snapshot,
        "reviewed_files": sorted({c["path"] for c in components if c["classification"] in {"authoritative_runtime", "runtime_support"}}),
        "active_runtime_files_reviewed": sum(1 for c in components if c["classification"] == "authoritative_runtime"),
        "note": "Batch 03 reviews active runtime scope only; this is not a full repository line audit.",
    }
    write_json(OUT / "FILE_AUDIT_LEDGER_BATCH03.json", coverage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
