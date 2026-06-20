# Phase Status

This file tracks the gated full-build phases. A phase is not complete until implementation, tests, executed commands, failure fixes, status documentation, and a commit are all done.

## Phase 0 - Product Truth And Documentation Baseline

- Status: implementation and verification complete; commit pending
- Files changed:
  - `README.md`
  - `docs/CODEX_FULL_BUILD_BASELINE.md`
  - `docs/PHASE_STATUS.md`
  - `docs/CURRENT_CAPABILITIES.md`
  - `docs/CAPABILITY_MATRIX.md`
  - `docs/CIVILIZATION_FOUNDATION.md`
  - `docs/CLAIMS_POLICY.md`
  - `tests/test_docs_claims.py`
  - `agents/core/memory/learning_loop.py`
  - `backend/src/db/run_migrations.py`
- Tests added:
  - `tests/test_docs_claims.py`
- Commands run:
  - `make test` - failed at baseline on UUID JSON serialization in `test_learning_loop_consolidates_semantics`
  - `npm test` in `backend` - failed because Postgres/Kafka services were unavailable
  - `npm run build` in `backend` - passed
  - `npm test` in `frontend` - failed because `jest` was not found
  - `npm run build` in `frontend` - passed with an existing hook dependency warning
- `python3 -m pytest tests/test_docs_claims.py` - passed, 2 tests
- `python3 -m pytest tests/e2e/test_memory_lifecycle.py::test_learning_loop_consolidates_semantics` - passed, 1 test
- `make migrate` - passed, 23 migrations applied
- `make test` - passed:
  - Python: 227 passed
  - migrations: 23 applied
  - backend Jest: 32 passed
  - frontend build: passed
- Pass/fail status: passed
- Failures fixed:
  - Converted consolidated memory evidence IDs to strings before JSON storage.
  - Added repo root to the migration runner import path so `agentco_security.env_guard` remains active under `make migrate`.
- Remaining risks:
  - Backend tests emit an existing Kafka partitioner warning and worker shutdown warning.
  - Frontend build emits an existing `react-hooks/exhaustive-deps` warning in `frontend/src/app/audit/page.tsx`.
  - Standalone frontend `npm test` still fails because `jest` is not installed/resolvable; `make test` does not invoke it.
- Commit hash: `3f454ec`

## Phase 1 - Calibration Independence Engine

- Status: implementation and verification complete; commit pending
- Files changed:
  - `calibration/ledger/prediction_ledger.py`
  - `calibration/resolution/resolution_service.py`
  - `calibration/resolution/source_independence.py`
  - `calibration/tests/test_resolution_independence_engine.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `calibration/tests/test_resolution_independence_engine.py`
- Commands run:
  - `python3 -m pytest calibration/tests/test_resolution_independence_engine.py` - failed once due to a test setup issue, then passed with 11 tests
  - `python3 -m pytest calibration reserve/tests tests/integration tests/test_trust_monotonicity.py tests/test_weighting_floor_fix.py` - failed once because legacy registrations were interpreted as same-source resolutions, then passed with 103 tests
  - `make test` - passed:
    - Python: 238 passed
    - migrations: 23 applied
    - backend Jest: 32 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed:
  - Corrected missing-lineage test setup so it clears both explicit and legacy lineage.
  - Changed legacy claim lineage to use the pre-registered ledger entry when no explicit claim source URL is provided, preserving existing tests while keeping explicit same-source URL rejection strict.
- Remaining risks:
  - New lineage fields are enforced in the Python/domain service layer; DB persistence of the new resolution lineage columns is not implemented in this phase.
  - Rejection audit events are stored in the resolution service's in-memory audit event list; durable audit integration remains future work.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `80196c0`

## Phase 2 - Institution Kernel Hardening

- Status: implementation and verification complete; commit pending
- Files changed:
  - `civilization/services/institution_service.py`
  - `civilization/services/review_service.py`
  - `civilization/services/reputation_service.py`
  - `reserve/migrations/006_civilization.sql`
  - `tests/civilization/test_institution_kernel_hardening.py`
  - `docs/INSTITUTION_KERNEL.md`
  - `docs/CIVILIZATION_MEMORY_EVENTS.md`
  - `docs/INSTITUTION_KERNEL_HARDENING_STATUS.md`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_institution_kernel_hardening.py`
- Commands run:
  - `python3 -m pytest tests/civilization` - passed, 27 tests
  - `python3 -m pytest calibration reserve/tests tests/civilization tests/e2e/test_institution_operating_loop.py tests/test_trust_monotonicity.py tests/test_weighting_floor_fix.py` - failed once on role allowlist missing `engineer`, then passed with 95 tests
  - `make test` - passed:
    - Python: 244 passed
    - migrations: 23 applied
    - backend Jest: 32 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed:
  - Added `engineer` to the validated membership role allowlist to preserve the existing institution operating loop.
- Remaining risks:
  - Automatic reputation-floor probation/suspension remains documented as a remaining risk, not fully implemented.
  - Department-level governance remains represented by shared governance/memory primitives, not a dedicated department governance table.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `226cce1`

## Phase 3 - Governed API Productization

- Status: implementation and verification complete; commit pending
- Files changed:
  - `backend/src/server.ts`
  - `backend/src/routes/governed.routes.ts`
  - `backend/tests/governed-api.test.ts`
  - `docs/openapi/agentco-governed-api.yaml`
  - `sdk/python/agentco_client.py`
  - `sdk/typescript/agentco-client.ts`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `backend/tests/governed-api.test.ts`
- Commands run:
  - `npm test -- governed-api.test.ts` in `backend` - passed, 4 tests
  - `npm run build` in `backend` - passed
  - `make test` - passed:
    - Python: 244 passed
    - migrations: 23 applied
    - backend Jest: 36 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and build passed on first run.
- Remaining risks:
  - Governed API handlers use an in-memory service boundary in this phase; durable persistence and full OpenAPI schema expansion remain future work.
  - Python and TypeScript SDKs are stubs for the governed API surface.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `28b0139`

## Phase 4 - RBAC, Service Identities, And Security Model

- Status: implementation and verification complete; commit pending
- Files changed:
  - `backend/src/security.ts`
  - `backend/src/routes/governed.routes.ts`
  - `backend/tests/governed-api.test.ts`
  - `backend/tests/rbac.test.ts`
  - `docs/SECURITY_MODEL.md`
  - `docs/THREAT_MODEL.md`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `backend/tests/rbac.test.ts`
- Commands run:
  - `npm test -- rbac.test.ts governed-api.test.ts security.test.ts` in `backend` - passed, 14 tests
  - `npm run build` in `backend` - passed
  - `make test` - passed:
    - Python: 244 passed
    - migrations: 23 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and build passed on first run.
- Remaining risks:
  - RBAC policy is code-defined, not yet backed by durable policy storage.
  - Key rotation and rate limiting are documented hooks/stubs, not full infrastructure implementations.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `e7bbb15`

## Phase 5 - Society Layer

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/007_society.sql`
  - `civilization/services/society_service.py`
  - `civilization/services/society_governance_service.py`
  - `civilization/services/society_reputation_service.py`
  - `civilization/services/society_memory_service.py`
  - `tests/civilization/test_society_layer.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_society_layer.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_society_layer.py` - failed once due to test transaction setup for reputation guard, then passed with 5 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 95 tests
  - `make test` - passed:
    - Python: 249 passed
    - migrations: 24 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed:
  - Updated society reputation test setup to use a transaction-scoped authorized reputation update instead of weakening the reputation guard.
- Remaining risks:
  - Society services are DB-backed but intentionally minimal; inter-institution review routing and resource allocation remain future hardening.
  - Society dispute handling is represented through society governance decisions, not the full judiciary model planned for Phase 7.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `350d78d`

## Phase 6 - Jurisdiction Engine

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/008_jurisdiction.sql`
  - `civilization/services/jurisdiction_service.py`
  - `tests/civilization/test_jurisdiction.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_jurisdiction.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_jurisdiction.py` - passed, 4 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 99 tests
  - `make test` - passed:
    - Python: 253 passed
    - migrations: 25 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and full gate passed on first run.
- Remaining risks:
  - Delegated authority checks are scoped to parent action/output matching; deeper constraint evaluation remains future hardening.
  - External review requirement is recorded and returned as an allowed authority flag, but workflow routing remains later integration work.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `bbe3c0f`

## Phase 7 - Dispute / Judiciary Layer

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/009_disputes.sql`
  - `civilization/services/dispute_service.py`
  - `tests/civilization/test_dispute_judiciary.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_dispute_judiciary.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_dispute_judiciary.py` - passed, 4 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 103 tests
  - `make test` - passed:
    - Python: 257 passed
    - migrations: 26 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and full gate passed on first run.
- Remaining risks:
  - Judiciary penalties are recorded but not yet propagated into the Phase 8 economy or broader authority reductions.
  - Dispute lifecycle is DB-backed and tested but minimal; mediation workflow and richer evidence review remain future hardening.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `3f7cae1`

## Phase 8 - Institutional Economy

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/010_economy.sql`
  - `civilization/services/economy_service.py`
  - `tests/civilization/test_economy.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_economy.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_economy.py` - passed, 5 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 108 tests
  - `make test` - passed:
    - Python: 262 passed
    - migrations: 27 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and full gate passed on first run.
- Remaining risks:
  - Economy resources are abstract and DB-backed, but not yet wired into every production action path.
  - High reputation unlocking larger authority scope is represented by separate jurisdiction/reputation layers, not automatic economy-to-jurisdiction expansion.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `0e344a1`

## Phase 9 - Civilization Constitution And Law Registry

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/011_civilization_constitution.sql`
  - `civilization/services/civilization_service.py`
  - `tests/civilization/test_civilization_constitution.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_civilization_constitution.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_civilization_constitution.py` - passed, 5 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 113 tests
  - `make test` - failed once due to a migration table-name conflict with Institution Kernel memory, then passed:
    - Python: 267 passed
    - migrations: 28 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed:
  - Renamed constitutional memory table to `civilization_constitution_memory_events` to avoid conflicting with the existing Institution Kernel `civilization_memory_events` schema.
  - Updated focused fixture to apply Institution Kernel migration before Society migration.
- Remaining risks:
  - Constitution governance is DB-backed and tested but minimal; quorum semantics are numeric and not yet tied to real voting identities.
  - Emergency powers block high-risk checks via service helper but are not yet wired into every mutation route.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `94e1bf3`

## Phase 10 - Civilization Memory And Precedent System

- Status: implementation and verification complete; commit pending
- Files changed:
  - `reserve/migrations/012_civilization_memory.sql`
  - `civilization/services/civilization_memory_service.py`
  - `tests/civilization/test_civilization_memory.py`
  - `docs/PHASE_STATUS.md`
- Tests added:
  - `tests/civilization/test_civilization_memory.py`
- Commands run:
  - `python3 -m pytest tests/civilization/test_civilization_memory.py` - passed, 3 tests
  - `python3 -m pytest tests/civilization calibration reserve/tests tests/e2e/test_institution_operating_loop.py` - passed, 116 tests
  - `make test` - passed:
    - Python: 270 passed
    - migrations: 29 applied
    - backend Jest: 42 passed
    - frontend build: passed
- Pass/fail status: passed
- Failures fixed: none after implementation; focused tests and full gate passed on first run.
- Remaining risks:
  - Memory summaries and lineage are DB-backed but not yet exposed in dashboard/API views.
  - Causal links table exists but causal explanation workflows remain future hardening.
  - Backend Jest still emits existing Kafka partitioner and worker shutdown warnings under `make test`.
  - Frontend build still emits the existing hook dependency warning in `frontend/src/app/audit/page.tsx`.
- Commit hash: `323af59`

## Later Phases

Phases 11-14 have not started. They must remain blocked until Phase 10 has passed and been committed.
