# AgentCo Post-Fix Runnability Verification

Date: 2026-06-25  
Repo path verified: `/Users/Zet/Agentco` (`pwd` resolved to `/Users/Zet/agentco`)  
Commit verified: `3fa6cb6e5c5b595f983d1724d9826f7417226d0a`

## Final Verdict

`STILL_PARTIALLY_RUNNABLE`

This repository cannot be upgraded to `RUNNABLE_LOCAL_NATIVE`, `RUNNABLE_OFFLINE_FIXTURE`, or `RUNNABLE_WITH_FALLBACKS` based on the commands run in this verification. Some components work, but the reported fix phases are not present in this mounted repo, and key local run contracts fail or are missing.

Important context: the latest commits in this repo are:

```text
3fa6cb6 feat: Phase 5 Calibration Step 2.5 — Deduplication & Validation Prep
eedbb57 feat: Phase 5 Calibration Step 2 — Real Claims from Arxiv Papers
c02243c feat: Phase 5 Calibration Step 1 — Initial Data Collection
4715852 feat: Phase 5 Calibration Groundwork - Foundation for Safe Self-Modification
1c185cd fix: Evidence persistence and OpenAI extraction improvements
```

The expected post-fix commits for runnability/resilient doctor orchestration are not in this repo state.

## Run Type

Not a clean full-stack run, not a verified local-native run, and not a verified offline-fixture run.

Observed working pieces:

- Python 3.13 exists.
- Backend TypeScript build passes.
- `runtime/tests` pass under Python 3.13.

Observed blockers:

- Backend Jest default tier fails.
- Frontend tests/lint/build fail.
- Migration target fails.
- Runtime doctor/fallback targets are missing.
- North-star benchmark target and tests are missing.
- Live OpenAI verifier scripts are missing.
- Override read route remains unprotected.

## Fix Verification Matrix

| Fix area | Verified result | Evidence |
|---|---|---|
| Python/runtime reproducibility | partial | `python3.13 --version` passed; `.python-version`, `requirements-dev.txt`, `requirements-runtime.txt`, and `make python-check` are absent. |
| Native Postgres migration path | failed | `make verify-migrations-native` target missing; existing `make migrate` fails: `psycopg2 not installed`. |
| Override route auth protection | failed | `backend/src/routes/override.routes.ts` has unauthenticated `fastify.get('/api/overrides', ...)`; in-process probe hit handler and returned 500 due DB access, not 401. |
| Resolution-service verification path | not verified | `make verify-resolution-service` target missing; `resolution_service_verification.json` absent. |
| North-star cross-domain benchmark | missing | `make north-star-smoke` target missing; `evals/north_star_cross_domain/tests` absent; result files absent. |
| Runtime modes | missing | `runtime/orchestration` package absent. |
| Service doctor | missing | `make doctor`, `make doctor-offline`, `make doctor-production` targets missing; doctor reports absent. |
| Fallback orchestration | missing | `make run-offline-fixture` and `make run-best-effort` targets missing. |
| Best-effort run | missing | no command target exists. |
| Updated docs/reports | missing/partial | `reports/system_run/latest` had to be created during this verification; expected doctor/goal/OpenAI reports were absent. |

## Command Results

| Command | Exit | Result |
|---|---:|---|
| `git status --short` | 0 | clean at start |
| `git rev-parse HEAD` | 0 | `3fa6cb6e5c5b595f983d1724d9826f7417226d0a` |
| `git log --oneline -5` | 0 | latest commits do not include the reported fix phases |
| `find reports/system_run/latest ...` | nonzero | directory did not exist initially |
| `find results -maxdepth 3 ...` | 0 | existing result artifacts are unrelated to the requested north-star benchmark |
| `python3.13 --version` | 0 | Python 3.13.9 |
| `make python-check` | 2 | missing target |
| `make verify-migrations-native` | 2 | missing target |
| `make verify-resolution-service` | 2 | missing target |
| `cd backend && npm test -- --runInBand --forceExit` | 1 | 16 failed suites, 7 passed; 85 failed tests, 120 passed |
| `cd backend && npm run build` | 0 | TypeScript build passed |
| `node dist/server.js` with `PORT=3101` | 1 | sandbox blocked listen with `EPERM`; in-process probe used instead |
| Fastify inject `GET /api/overrides` unauthenticated | 0 command / bad app behavior | returned 500 after DB access, proving route did not reject unauthenticated request before handler |
| `cd frontend && npm test` | 127 | `jest: command not found` |
| `cd frontend && npm run lint` | 1 | `react/no-unescaped-entities` errors in `src/app/autonomy/page.tsx` |
| `cd frontend && npm run build` | 1 | build failed at lint/type stage for same lint errors |
| `make doctor-offline` | 2 | missing target |
| `make doctor` | 2 | missing target |
| `make doctor-production` | 2 | missing target |
| `make run-offline-fixture` | 2 | missing target |
| `make run-best-effort` | 2 | missing target |
| `make north-star-smoke` | 2 | missing target |
| `python3.13 -m pytest evals/north_star_cross_domain/tests -q` | 4 | directory not found |
| `make verify-system-offline` | 2 | missing target |
| `make verify-system-native` | 2 | missing target |
| `python3 scripts/verify_openai_connectivity.py` | 2 | script missing |
| `python3 scripts/verify_agentco_goal_run.py` | 2 | script missing |
| `python3.13 -m pytest runtime/orchestration/tests -q` | 4 | directory not found |
| `python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q` | 4 | file not found |
| `python3.13 -m pytest runtime/tests -q` | 0 | 41 passed |
| `make migrate` | 2 | backend build passed, then Python migration failed: `psycopg2 not installed` |

## Backend Test Failure Summary

The default backend Jest tier failed with several independent root causes:

- Schema drift: tests/services expect columns such as `autonomy_goals.text`, `autonomy_goals.institution_id`, `departments.entity_type`, `new_reputation`, and others that are not present in the active schema.
- Invalid ID assumptions: some tests pass non-UUID strings into UUID columns.
- Missing dependency: `tests/phase1-integration.test.ts` imports `axios`, but it is not installed/typed.
- Kafka unavailable: event bus integration tests fail when Kafka cannot connect.
- DB connectivity/config mismatch: several integration tests try `/tmp/.s.PGSQL.5433`.
- Missing `LLM_API_KEY` in some backend tests when not loaded from `.codex.env`.
- TypeScript test helper issue: `it.skipIf` is not available in the configured Jest typings.

This blocks any upgrade to a runnable local-native verdict.

## Override Route Auth Result

Failed.

Source inspection:

```ts
fastify.get('/api/overrides', async (req, reply) => { ... })
fastify.get('/api/overrides/overdue', async (_req, reply) => { ... })
```

Both read routes lack `requireApiKey` or scoped auth. The manual in-process probe returned 500 because the route reached database code and the sandbox blocked DB access. A secure implementation should reject unauthenticated reads with 401 before any DB handler work.

## Migration Verification Result

Failed.

`make verify-migrations-native` is absent. The existing `make migrate` path still runs:

```text
python3 src/db/run_migrations.py
ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary
```

This is the old ambiguous Python migration dependency failure, not the resilient TypeScript migration path requested.

## Resolution-Service Verification Result

Not verified.

`make verify-resolution-service` is absent, and no `reports/system_run/latest/resolution_service_verification.json` was generated.

## Runtime Doctor And Fallback Result

Missing.

No `runtime/orchestration` package exists. All expected doctor/best-effort targets are missing:

- `make doctor-offline`
- `make doctor`
- `make doctor-production`
- `make run-offline-fixture`
- `make run-best-effort`

No doctor report exists, so no selected runtime mode, fallback list, disabled capability list, or safe next command can be verified.

## North-Star Benchmark Result

Missing.

`make north-star-smoke` is absent. `results/north_star_cross_domain/latest.json`, `latest.md`, and `evals/north_star_cross_domain/tests` are absent. No four-domain cross-domain smoke benchmark was verified.

## OpenAI And Goal-Run Result

Not verified.

`.codex.env` exists and contains `LLM_API_KEY` by key name, but the expected verification scripts are absent:

- `scripts/verify_openai_connectivity.py`
- `scripts/verify_agentco_goal_run.py`

No `openai_connectivity.json` or `goal_run.json` existed before this verification.

## Frontend Result

Failed.

- `npm test`: failed because `jest` command is missing.
- `npm run lint`: failed with `react/no-unescaped-entities`.
- `npm run build`: failed because lint/type validation failed.

## Performance Summary

Only limited timings were observed:

- Backend build completed in a few seconds and passed.
- Backend Jest default tier ran about 60 seconds and failed.
- Frontend build reached compile stage but failed during lint/type checks.
- Runtime Python tests completed quickly and passed: 41 tests in about 0.5s.

No doctor/best-effort performance metrics exist in this repo.

## Remaining Blockers

1. The reported fix commits are not present in this repository state.
2. Add or merge the runtime doctor/orchestration layer.
3. Add Python 3.13 runtime contract files and `make python-check`.
4. Replace or supplement Python migration runner with a working native migration verification path.
5. Protect `GET /api/overrides` and `GET /api/overrides/overdue`.
6. Add `make verify-resolution-service` with safe authorized/unauthorized checks.
7. Add `make doctor*`, `make run-*`, `make verify-system-*`.
8. Add north-star cross-domain benchmark and tests.
9. Fix backend schema/test drift and missing dependencies.
10. Fix frontend test dependency and lint errors.

## Exact Next Commands For A Developer

```bash
git log --oneline -20
rg -n "fastify.get\\('/api/overrides" backend/src/routes/override.routes.ts
cd backend && npm test -- --runInBand --forceExit
cd frontend && npm run lint
make migrate
```

After merging the missing fix phase, rerun:

```bash
make python-check
make verify-migrations-native
make verify-resolution-service
make doctor-offline
make doctor
make run-offline-fixture
make run-best-effort
make north-star-smoke
make verify-system-offline
make verify-system-native
```
