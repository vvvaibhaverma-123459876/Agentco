# Agentco Session Handoff

## Current Gate

**GATES 0-17 are complete for the implemented repo scope.**

## Completed This Session

- Replaced README legacy autonomous-company framing with the single present-day evidence-governed control-plane promise.
- Added status-label taxonomy to README.
- Added `frontend/src/lib/api.ts` so frontend imports resolve in source and write calls attach `x-api-key` when `NEXT_PUBLIC_AGENTCO_API_KEY` is set.
- Added backend write-auth middleware for non-GET requests when `AGENTCO_API_KEY` is set.
- Fixed `backend/src/db/run_migrations.py` migration directory path.
- Added `Makefile` with `make dev`, `make migrate`, and `make smoke`.
- Created refoundation docs and initial truth ledger.
- Renumbered duplicate memory lifecycle migration to `017_agent_memories_lifecycle.sql`.
- Added canonical refoundation schema migration `018_refoundation_canonical_schema.sql` and rollback contract.
- Added `calibration/evidence` Evidence Kernel with source-independence engine, claim/evidence APIs, promotion/demotion, contradiction checks, source reliability, and claim graph.
- Added Gate 1 and Gate 2 regression tests.
- Wired Gate 0 smoke into CI.
- Added durable execution service, workflow task migration, and dispatch route integration.
- Added action attestation verifier and backend provenance service.
- Added uncertainty stack with conformal wrapper, semantic uncertainty, metrics, and abstention.
- Added Memory Kernel with immutable experiential memory and mutable operational memory split.
- Added universal ingestion pipeline with text, web/HTML, and code adapters.
- Added Gate 3-7 regression tests.
- Added autonomous learning loop, dynamic agent/skill registry, governance policy engine, society kernel, simulation world lab, self-modification kernel, and Model Foundry trace pipeline.
- Added Gate 8-14 regression tests.
- Added validation suite with evidence-quality-labelled reports, validation/governance console routes/pages, and CI master gate.
- Added Gate 15-17 regression tests.

## Commands Run

```bash
python3 -m pytest calibration runtime learning synthesis evals/regression -q
```

Result: initially `115 passed in 1.30s`. A later `make smoke` run hit 8 Postgres connection errors from `evals/regression/test_pg_ledger_immutability.py` and `evals/regression/test_pg_ledger_persistence.py` because localhost DB access was denied by the sandbox. `make smoke` was updated to exclude those DB-backed tests; run them separately when local Postgres is available.

```bash
make smoke
```

Result after update: `107 passed in 0.76s`; backend/frontend checks reported `node_modules` missing and told the operator to run `make dev`.
Final result after Gates 15-17 additions: `139 passed`.

```bash
npx tsc --noEmit
```

Result in backend/frontend: failed before typecheck because npm registry access is blocked and `node_modules` is missing.

```bash
npm ci
cd backend && ./node_modules/.bin/tsc --noEmit
cd frontend && ./node_modules/.bin/tsc --noEmit
cd backend && npm run build
cd frontend && npm run build
```

Result after approved dependency install: backend/frontend TypeScript checks passed; backend/frontend builds passed. Frontend build reported one warning: `src/app/audit/page.tsx` has a missing dependency in a `useEffect`.
Final frontend build after hook fix passed without that warning.

```bash
AGENTCO_TEST_DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco python3 -m pytest evals/regression/test_pg_ledger_immutability.py evals/regression/test_pg_ledger_persistence.py -q
```

Result after approved local Postgres access: `8 passed`.

```bash
DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm run db:migrate
```

Result after fixing migration 016 and adding migration 018: migrations complete.

```bash
DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm run db:migrate
```

Result after adding migration 019: migrations complete.

Durable execution smoke produced `{"status":"done","kind":"health_check_result","attested":true}` against local Postgres. The node process had to be interrupted after output because KafkaJS kept a producer handle open.

```bash
make master-gate
```

Result: passed. It ran smoke tests, validation report generation, backend build, and frontend build.

## Files Changed

- `README.md`
- `Makefile`
- `frontend/src/lib/api.ts`
- `frontend/src/app/layout.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/app/dashboard/page.tsx`
- `backend/src/server.ts`
- `backend/src/db/run_migrations.py`
- `docs/refoundation/*`
- `docs/architecture/agentco_architecture.md`
- `backend/src/db/migrations/016_resolution_service_role.sql`
- `backend/src/db/migrations/017_agent_memories_lifecycle.sql`
- `backend/src/db/migrations/018_refoundation_canonical_schema.sql`
- `backend/src/db/rollbacks/018_refoundation_canonical_schema.down.sql`
- `calibration/evidence/*`
- `evals/regression/test_canonical_schema_gate1.py`
- `evals/regression/test_evidence_kernel_gate2.py`
- `scripts/gate0_check.py`
- `backend/src/db/migrations/019_durable_execution.sql`
- `backend/src/services/durable-execution.service.ts`
- `backend/src/services/provenance.service.ts`
- `provenance/*`
- `calibration/uncertainty/*`
- `memory_kernel/*`
- `ingestion/*`
- `evals/regression/test_gate3_durable_execution.py`
- `evals/regression/test_gate4_provenance_attestation.py`
- `evals/regression/test_gate5_uncertainty_stack.py`
- `evals/regression/test_gate6_memory_kernel.py`
- `evals/regression/test_gate7_ingestion.py`
- `validation/*`
- `scripts/run_real_world_validation.py`
- `backend/src/routes/governance.routes.ts`
- `frontend/src/app/validation/page.tsx`
- `frontend/src/app/governance/page.tsx`
- `evals/regression/test_gate15_validation.py`
- `evals/regression/test_gate16_operator_console.py`
- `evals/regression/test_gate17_ci_master.py`

## Known Risks

- Backend and frontend `npm audit --audit-level=moderate` currently report `0 vulnerabilities` after dependency updates.
- Docker Compose config now validates, local bind sources are covered by `tests/test_compose_bind_sources.py`, Prometheus/Grafana/OTel local config files exist, and `make docker-startup-verify` passed once Docker was running.
- The canonical civilization vertical slice now passes after `resolution_service` grant repair and `prediction_ledger` Reserve-field compatibility fixes. A backend L14 runtime service now exposes graph/tick API routes, persists a core coordinator reachability tick, and has a bounded scheduler with run-once/start/stop controls. Full civilization is still not fully integrated: the remaining gap is the complete always-on L14 coordinator service graph, durable multi-society runtime trace, and reachability proof across every implemented service.
- Durable execution standalone smoke now uses shared runtime shutdown and exits after local Postgres verification even when Kafka is unavailable.
- Gate 15 has optional live endpoint connectors and now labels configured-but-unavailable connectors as `LIVE-UNAVAILABLE` instead of fixture evidence. No real third-party endpoint credentials are configured in this workspace.

## Exact Next Steps

1. Complete full L14 civilization coordinator integration beyond the verified vertical slice.
2. Configure real third-party benchmark endpoint credentials and run `python3.13 scripts/run_real_world_validation.py` with `WORKFLOW_API_URL`, `SAFETY_API_URL`, and/or `EVIDENCE_API_URL`.
