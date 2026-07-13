# Remediation 03: Runtime Architecture And Integration

## Scope

This batch audits active runtime architecture, authoritative implementations, reachability, CI convergence, and local-real integration across PostgreSQL, Redis, Kafka, backend, outbox worker, Python specialist spawning, and governance-adjacent runtime paths.

It does not claim hosted production readiness, general intelligence, longitudinal learning, or autonomous production mutation proof.

## Files Reviewed

Runtime files reviewed in this batch are recorded in `docs/audit/current/FILE_AUDIT_LEDGER_BATCH03.json`.

Primary files inspected:

- `backend/src/server.ts`
- `backend/src/health.ts`
- `backend/src/db/kafka.ts`
- `backend/src/services/event-log.service.ts`
- `backend/src/services/event-bus.service.ts`
- `backend/src/services/transactional-outbox.service.ts`
- `backend/src/workers/outbox-worker.ts`
- `backend/src/services/team-activation.service.ts`
- `agents/autonomy/*`
- `runtime/base_agent/*`
- `runtime/controlled_learning/*`
- `runtime/self_improvement/*`
- `.github/workflows/ci.yml`
- `.github/workflows/clean-room-audit.yml`

## Architecture Discovered

The executable local runtime is:

```text
Fastify backend
  -> PostgreSQL migrations and repositories
  -> Redis where configured
  -> EventLogService
  -> event_outbox
  -> OutboxWorker
  -> Kafka
  -> Kafka consumer
  -> TeamActivationService
  -> python3.13 -m agents.autonomy.<role>
```

The standalone `learning/` and `synthesis/` trees are experimental/supporting code in this batch because no active backend startup path was found that deploys them as independent production processes.

## Authoritative Implementation Decisions

See `docs/audit/current/AUTHORITATIVE_IMPLEMENTATIONS.md`.

Key decisions:

- Backend Fastify server is the authoritative HTTP entry point.
- PostgreSQL migrations under `backend/src/db/migrations` are the authoritative schema path.
- `EventLogService -> event_outbox -> OutboxWorker -> Kafka` is the verified transactional outbox path.
- `EventBusService -> event_bus_outbox` is a parallel active path and remains a consolidation backlog item.
- Python BaseAgentV2 runtime is authoritative for governed active agents.
- V1 specialists remain compatibility-layer subprocess agents behind the TS `TeamActivationService`.

## Runtime Evidence

`make audit-runtime-integration` provisions isolated local services and writes:

```text
artifacts/runtime-integration/<run-id>/EXECUTION_LEDGER.json
artifacts/runtime-integration/<run-id>/INTEGRATION_SUMMARY.md
artifacts/runtime-integration/<run-id>/process-logs/
artifacts/runtime-integration/<run-id>/http-traces/
```

The command proves:

- PostgreSQL container readiness
- Redis ping/set/get
- Kafka metadata readiness
- migrations from zero
- backend build and readiness
- unauthenticated route rejection
- authenticated backend route access
- transactional outbox row creation
- outbox relay to Kafka
- Kafka consumer readback
- worker restart/idempotency proof with no duplicate publication
- Python agent dispatch E2E with Kafka available
- specialist subprocess spawn over HTTP
- outbox failure injection visibility with a durable `dead_lettered` row
- cleanup of containers, network, and volumes

## Defects Found

Findings are recorded in `docs/audit/current/RUNTIME_INTEGRATION_FINDINGS.json`.

- `RTI-001` CI divergence: resolved in this batch.
- `RTI-002` parallel event outbox implementations: backlog, non-blocking for the verified event-log outbox path.

## Negative And Failure-Injection Results

The runtime harness includes:

- unauthenticated HTTP request check
- outbox publisher failure injection that creates an event, forces publish failure, and verifies `event_outbox.status = dead_lettered`
- outbox worker restart/idempotency check that reruns the relay after successful publication and verifies no duplicate publish
- Kafka consumer readback failure if no message arrives
- cleanup verification failure if resources remain

Focused unit controls are in `tests/test_runtime_integration_controls.py`.

## Remaining Limitations

- Full browser UI E2E is not executed in Batch 03.
- Hosted Kubernetes, backup/restore, staging rollback, alert delivery, and live provider integrations remain unverified.
- Long-horizon mission claims remain unproven.
- EventBus outbox and EventLog outbox require later consolidation.

## Rollback

Revert the Batch 03 commits and rerun:

```text
make release-gate
make audit-clean-room
```

After rollback, runtime integration evidence and CI convergence improvements will be absent.

## Commit

Final commit SHA is recorded in the final handoff response and runtime integration ledger.
