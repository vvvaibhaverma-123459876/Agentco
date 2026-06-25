# Runnability Fix Module

## Verdict

Completed and verified.

This module fixes the highest-priority concrete defects from `AGENTCO_RUNNABILITY_REPORT.md` before moving on to new functionality.

## Fixes

| Defect | Fix | Evidence |
|---|---|---|
| `/api/overrides` exposed pending override data without auth | Added `requireScope('governance:mutate')` to `GET /api/overrides` and `GET /api/overrides/overdue` | `fix_security_test.log`, `fix_backend_jest.log` |
| `npm run db:migrate` used Python runner blocked by missing `psycopg2` and broken default Python packaging | Switched backend `db:migrate` to existing TypeScript `pg` migration runner and added `RESOLUTION_SERVICE_PASSWORD` substitution | `fix_migration_run.log` |
| Goal verifier could register primary ledger predictions but could not resolve them | Added separate resolution-service DSN path and used it for `prediction_ledger` resolution updates | `fix_goal_run_live.log`, `goal_run.json` |
| Goal verifier success did not require primary ledger resolution | Required `prediction_ledger_resolution_update` in DB success criteria | `goal_run.json` |

## Verification Commands

| Command | Result |
|---|---|
| `cd backend && npm test -- security.test.ts --runInBand --forceExit` | passed: 6 tests |
| `cd backend && npx tsc --noEmit` | passed |
| `cd backend && npm run db:migrate` | passed; all migrations skipped as already applied |
| `python3 scripts/verify_agentco_goal_run.py` | passed live OpenAI + Postgres |
| `cd backend && npm test -- --runInBand --forceExit` | passed: 25 suites, 156 tests |
| `python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q` | passed: 6 tests |
| `make verify-system-offline` | passed |

## Final Live Goal Run

| Field | Value |
|---|---|
| Run ID | `goal-run-20260625T091846Z-b77b2ffe` |
| Mode | `live_openai` |
| Success | `true` |
| Total latency | `3451.46 ms` |
| Primary ledger insert | `da0e07f6-cfef-4698-8af5-edbcb4ca678d` |
| Primary ledger resolution update | passed |
| Legacy resolution insert | `goal-run-cb915f62b3ab` |
| Trust score insert | `0a0c5362-6c6b-4551-8532-b15be6641cb8` |
| Event insert | `37a6e0c5-b664-420b-a6a0-fadb5cc3c879` |

## Remaining Known Gaps

Docker-dependent infrastructure remains unavailable in this environment. The default `python3` environment still cannot run broad Python tests because its package installer is blocked by a local Python 3.14 `pyexpat`/libexpat issue; Python 3.13 can run the added verifier tests.
