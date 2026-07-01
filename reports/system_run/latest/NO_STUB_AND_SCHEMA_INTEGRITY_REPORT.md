# No-Stub And Schema Integrity Report

> **Historical/superseded status notice:** This report is retained for audit history. Do not treat old ledger-count, branch, or production-readiness language below as current truth. Current implementation status is tracked in `BUILD_LEDGER.yaml`, `docs/CURRENT_IMPLEMENTATION_REALITY.md`, and `reports/system_run/latest/mission_progress_verification.md`.

Date: 2026-06-29
Branch: `fix/runtime-integrity-and-production-honesty`

## Verdict

The no-stub/no-simulation ledger gates are now green, and the native Postgres
schema verifier now checks the runtime-critical task and civilization-routing
contract that previously drifted.

This is not a full production certification. `BUILD_LEDGER.yaml` still reports
`18/67` verified architecture items.

## What Was Fixed

| Area | Fix |
|---|---|
| No-stub gate | Removed scanner hits from comments/test labels and replaced abstract unsupported methods with explicit runtime errors. |
| Department schema drift | Added additive migrations `089`, `090`, and `091` so legacy `departments` tables expose and populate `institution_id`. |
| Task event contract | Added `092_agent_task_events_canonical_view.sql`, a canonical view over `autonomy_task_events`. |
| Migration verifier | Expanded `scripts/verify_migrations_native.py` beyond three tables to check task, work-request, department, allocation, and hierarchy schema. |
| Migration verifier tests | Added `tests/test_verify_migrations_native.py`, including the regression case for missing `departments.institution_id`. |
| Audit chain verification | Made audit verification ignore historical non-service rows without valid hash-chain link fields while still validating canonical row hashes. |
| Live verifier audit timestamps | Made Python verifier decision-log writes use monotonic millisecond timestamps to avoid ambiguous hash-chain ordering. |

## Commands Run

| Command | Result |
|---|---|
| `cd backend && npm run db:migrate` | Passed; applied migrations `089` through `092` during this repair. |
| `make verify-migrations-native` | Passed with stricter schema contract. |
| `python3.13 -m pytest tests/test_verify_migrations_native.py -q` | Passed: `2 passed`. |
| `cd backend && npx jest tests/phase1-integration.test.ts tests/phase2-long-term-coordination.test.ts --runInBand --forceExit` | Passed after schema repair. |
| `cd backend && npm test -- --runInBand --forceExit` | Passed: `42` suites passed, `287` tests passed, `1` skipped, `5` todo. |
| `cd backend && npx tsc --noEmit` | Passed. |
| `python3.13 -m pytest runtime/orchestration/tests runtime/tests tests/test_verify_agentco_goal_run.py tests/test_verify_agentco_multidomain_live_run.py tests/test_verify_memory_influence_live.py -q` | Passed: `78 passed`. |
| `python3.13 scripts/build_ledger.py status --json` | Passed; `no_stub=green`, `no_simulation=green`, both hit counts `0`. |

## Current Migration Verifier Contract

Required tables/views:

- `agent_tasks`
- `agent_task_events`
- `autonomy_goals`
- `decision_log`
- `departments`
- `institution_specialist_assignments`
- `institution_work_requests`
- `override_queue`
- `prediction_ledger`
- `specialist_allocation_history`

Required runtime columns include:

- `departments.institution_id`
- `departments.parent_id`
- `institution_work_requests.institution_id`
- `institution_work_requests.department_id`
- `institution_specialist_assignments.department_id`
- `specialist_allocation_history.work_request_id`
- `autonomy_goals.institution_id`
- `autonomy_goals.goal_depth`

## Remaining Honest Limits

- Production is still not certified because deployment secrets and Vault posture
  are not configured.
- Docker/Kafka/Redis/observability were smoke-tested previously, but this pass
  focused on code/schema integrity and did not rerun the full production smoke.
- The architecture ledger remains in progress at `18/67` verified.
- Some tests still use deterministic test providers; production guards reject
  those providers in staging/production paths.
