# Runtime Integrity Final Verification

Branch: `fix/runtime-integrity-and-production-honesty`

## Commands Run

| Command | Result |
| --- | --- |
| `cd backend && npx tsc --noEmit` | passed |
| local production-code secret scan (`git grep` with docs/tests/reports excluded) | passed |
| `python3.13 -m pytest tests/test_execute_durable_task.py -q` | passed: 6 tests |
| `cd backend && npm test -- security.test.ts runtime-mode.test.ts task-worker.test.ts agent-registry.test.ts --runInBand --forceExit` | passed: 4 suites, 19 tests |
| `python3.13 -m pytest tests/test_execute_durable_task.py tests/test_migration_inventory.py -q` | passed: 9 tests |
| `python3.13 -m pytest runtime/tests/test_base_agent_v2.py agents/tests/test_specialist_real_web_actions.py -q` | passed: 18 tests |
| `cd backend && npm test -- --runInBand --forceExit` | passed: 31 suites, 1 skipped, 250 tests passed, 5 todo |
| `cd frontend && npm test` | passed |
| `cd frontend && npm run lint` | passed |
| `cd frontend && npm run build` | passed |
| `cd backend && DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco npm run db:migrate` | passed; applied `075_agent_tasks_canonical_view.sql` |
| `DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco python3.13 scripts/execute_durable_task.py <health_check_task_id>` | passed; task stored `done` result |
| `DATABASE_URL=postgresql://agentco:password@localhost:5432/agentco python3.13 scripts/execute_durable_task.py <decision_task_id>` | expected fail-closed; exit code 2 and task stored `failed` with `UnsupportedFeatureError` |

## Verified Fixes

- Production-like detection now includes `AGENTCO_ENV=staging`, `AGENTCO_ENV=production`, and `NODE_ENV=production`.
- Backend startup rejects fallback/simulated/unsupported providers in production-like mode.
- `/health/runtime` reports active provider classifications and fallback state.
- Specialist shared secret no longer accepts default-insecure fallback in staging/production.
- Durable Python executor requires `DATABASE_URL`, reads `agent_tasks`, validates payloads, and marks unsupported task types as failed.
- `review` and `decision` tasks no longer produce synthetic success.
- Supervised task worker subprocess wrapper classifies timeout, malformed JSON, failed exit, and success.
- Agent dispatch is gated by an explicit runtime registry; non-runnable/library-only agents and unsupported task types are rejected.
- CI adds a production-code secret scan and Postgres service-backed backend migration/test path.
- Frontend write requests send both backend auth header conventions; autonomy API default now targets the actual backend port.
- README now states current implementation reality instead of claiming production readiness.

## Remaining Blockers

- Full production readiness still requires real deployment secrets, Vault, production DB/Kafka/Redis/observability posture, and environment-specific runbooks.
- Disabled migrations remain unsupported/future until enabled and integration-tested.
- `review` and `decision` durable task types are intentionally unsupported until real services are wired.
- Most listed dashboard agents are library-only unless present in `backend/src/agent-registry.ts`.
- Docker compose smoke was not rerun in this pass; local verification used native Postgres.
