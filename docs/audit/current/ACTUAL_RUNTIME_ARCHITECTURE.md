# Actual Runtime Architecture

Tracked structural snapshot input hash `8e5c6fc35cf48724e0e13c8c1e28c31f638bcac7bf988b576f4d555704cc985c`.

## Process Topology

- Verified active path: backend Fastify, PostgreSQL, Redis probe, Kafka, outbox worker, Python specialist subprocess.
- Configured but unexecuted path: browser-to-frontend proxy full UI path in this batch.
- Experimental path: standalone `learning/` and `synthesis/` modules not wired into deployed backend process.
- Historical path: `.disabled` routes and unsupported migrations.

## HTTP Request Topology

`backend/src/server.ts` registers route modules under default API-key protection, with public health probes.

## Agent Execution Topology

Active TS backend dispatch can spawn Python specialists through `TeamActivationService` using `python3.13 -m agents.autonomy.${role}`.

## Data Persistence Topology

PostgreSQL is authoritative for migrations, decision logs, event logs, resource ledgers, evidence, agent tasks, and runtime governance artifacts.

## Event And Outbox Topology

`EventLogService.appendWithClient()` writes `event_log` and `event_outbox` in one transaction. `OutboxWorker` relays to Kafka. `EventBusService` also owns an `event_bus_outbox`; this is a parallel active implementation and is recorded in `AUTHORITATIVE_IMPLEMENTATIONS.md`.

## Governance And Audit Topology

Python BaseAgentV2 uses audit writer and evidence capture; backend uses decision/event logs and route auth.

## Learning And Promotion Topology

Runtime packages implement evaluation, controlled learning, and self-improvement guards. Batch 03 treats long-horizon learning as unproven.

## Authentication And Authorization Topology

Backend default route auth is enforced in `server.ts`; tool and agent authorization are enforced by runtime protocol tests.

## Failure And Recovery Topology

Outbox rows remain pending/failed/dead-lettered with bounded attempts; restart recovery is checked by rerunning the outbox worker against retained rows.

## Deployment Topology

Local Docker Compose and CI workflows are configured. Hosted Kubernetes deployment is not proven in this batch.

## Claimed Architecture Versus Executable Architecture

The executable architecture is a supervised, evidence-governed local runtime. General intelligence, hosted production, and longitudinal improvement claims remain outside this batch.
