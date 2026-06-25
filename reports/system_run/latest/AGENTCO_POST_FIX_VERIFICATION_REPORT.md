# AgentCo Post-Fix Verification Report

Date: 2026-06-26

## Final Verdict

`RUNNABLE_LOCAL_NATIVE`

AgentCo is runnable in the verified local-native path on this machine: Python 3.13, backend build/tests, frontend smoke/lint/build, native Postgres, migrations, resolution-service guard verification, OpenAI connectivity, goal-run, service doctor, fallback orchestration, and north-star smoke all passed.

This is not a clean production/full-stack verdict. Production doctor correctly fails closed because production-grade Redis/Kafka/Vault/Prometheus/Grafana are not all running as real services.

AgentCo is also `RUNNABLE_OFFLINE_FIXTURE`: the offline fixture path completed without external services and clearly marked simulated behavior.

## Verified Fixes

| Area | Result | Evidence |
|---|---|---|
| Python 3.13 runtime | Pass | `make python-check`: Python 3.13.9, `41 passed` |
| Runtime modes | Pass | `python3.13 -m pytest runtime/orchestration/tests -q`: `7 passed` |
| Service doctor | Pass | `make doctor`: selected `local_native`, `can_continue=true` |
| Production doctor fail-closed | Pass | `make doctor-production`: selected production but exited nonzero with `can_continue=false` |
| Fallback orchestration | Pass | `make run-best-effort`: selected `local_native`, completed live goal run |
| Offline fixture mode | Pass | `make verify-system-offline`: completed offline fixture and north-star smoke, `13 passed` |
| Native verification path | Pass | `make verify-system-native`: completed local-native live goal run |
| Native migration verification | Pass | `make verify-migrations-native`: Postgres real, core schema real |
| Resolution-service path | Pass | `make verify-resolution-service`: service role real, trigger guard proven |
| Override route auth | Pass | doctor reports `sensitive_route_auth=real`; prior manual probe returned unauthenticated `401` |
| Backend build | Pass | `cd backend && npm run build` |
| Backend full Jest | Pass | `cd backend && DATABASE_URL=... npm test -- --runInBand --forceExit`: 22 suites passed, 1 skipped, 219 tests passed, 5 todo |
| Frontend smoke/lint/build | Pass | `cd frontend && npm test && npm run lint && npm run build` |
| OpenAI connectivity | Pass | `gpt-4o-mini`, latency 1513 ms, 61 tokens |
| Live goal run | Pass | `simulated=false`, decision `escalate`, validation score `1.0` |
| North-star smoke benchmark | Pass | 4 domains, deterministic aggregate `1.0`; marked smoke/skeleton |

## Runtime Mode and Fallbacks

Latest `doctor_report.json`:

| Field | Value |
|---|---|
| selected_runtime_mode | `local_native` |
| can_continue | `true` |
| safe_next_command | `make run-best-effort` |

Fallbacks used:

| Service | Fallback |
|---|---|
| Redis | `memory_cache` |
| Kafka | `in_process_event_bus` |
| Vault | `env_secret_provider` |
| Prometheus | `json_metrics_writer` |
| Grafana | `metrics_json_only` |

These are explicit fallbacks, not real infrastructure. Docker CLI and daemon were reachable during this verification, but the selected safe path was still `local_native`.

## Migration Verification

`reports/system_run/latest/migration_verification.json`:

| Check | Result |
|---|---|
| Postgres connectivity | `real` |
| Migration dependency | `real` (`ts-node src/db/migrate.ts`) |
| Core schema | `real` |
| Required tables | `decision_log`, `override_queue`, `prediction_ledger` |

Existing schema is accepted when required tables are present. Missing schema would fail clearly through this verifier.

## Resolution-Service Verification

`reports/system_run/latest/resolution_service_verification.json`:

| Check | Result |
|---|---|
| result | `success` |
| resolution_service path | `success` |
| ordinary agent path | `success` |
| unauthorized resolution guard | `success` |
| guard_not_bypassed | `true` |

The verifier proves the live trigger guard from metadata and configured credentials without printing secrets.

## Goal-Oriented Run

`reports/system_run/latest/goal_run.json`:

| Field | Value |
|---|---|
| mode | `live_openai` |
| simulated | `false` |
| decision | `escalate` |
| confidence | `0.65` |
| trusted confidence | `0.585` |
| validation score | `1.0` |
| OpenAI model | `gpt-4o-mini` |
| goal latency | 3156 ms |
| audit/event records | 11 file-backed verifier events |

The run is evidence-governed at the verifier level: it requires `ev1` and `ev2`, rejects unsupported SOC 2 Type II confirmation, rejects breach conflation, requires missing SOC 2 Type II report, signed DPA, and subprocessor list, and validates confidence bounds.

## North-Star Benchmark

`results/north_star_cross_domain/latest.json`:

| Dimension | Result |
|---|---|
| Domains | vendor risk, medical-triage-safe-info, financial-risk-disclosure, code-change-risk-review |
| Mode | `deterministic_fake` |
| Aggregate score | `1.0` |
| Domain transfer consistency | `1.0` |
| Claim | smoke/skeleton only; not proof of general intelligence |

## Command Results

Passed:

```text
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
python3.13 -m pytest runtime/orchestration/tests -q
python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q
python3.13 -m pytest evals/north_star_cross_domain/tests -q
python3 scripts/verify_openai_connectivity.py
python3 scripts/verify_agentco_goal_run.py
cd backend && npm run build
cd backend && DATABASE_URL=<local-native-postgres-dsn> npm test -- --runInBand --forceExit
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
```

Expected blocked/fail-closed:

```text
make doctor-production
```

Result: exited nonzero because production mode cannot continue without all critical production dependencies. This is correct fail-closed behavior, not a local-native blocker.

## Performance Summary

| Metric | Latest observed |
|---|---:|
| OpenAI connectivity latency | 1513 ms |
| OpenAI connectivity tokens | 61 |
| Goal-run latency | 3156 ms |
| Goal-run tokens | 350 |
| Backend full Jest | 91.624 s |
| Backend full Jest result | 22 suites passed, 1 skipped, 219 tests passed |
| Frontend build | passed |
| Python runtime tests | 41 tests in 0.38 s |
| Offline verification tests | 13 tests in 1.00 s |
| North-star aggregate | 1.0 across 4 deterministic smoke domains |

## Real vs Fallback vs Simulated

| Capability | Status |
|---|---|
| Native Postgres connectivity | real |
| Core schema/migrations | real |
| Backend TypeScript build | real |
| Backend Jest suite | real local-native test coverage |
| Frontend build | real |
| OpenAI call | real |
| Resolution-service credential path | real |
| Override route auth protection | real |
| Kafka event bus | fallback in local-native |
| Redis cache | fallback in local-native |
| Vault secret provider | fallback in local-native |
| Prometheus/Grafana observability | fallback JSON/no UI in local-native |
| Offline fixture LLM | simulated by design |
| North-star cross-domain benchmark | deterministic smoke/skeleton, not GI proof |
| Goal-run event/audit trail | file-backed verifier events, not full DB audit integration |

## Remaining Blockers

1. Production runnability still requires real Kafka/Redis/Vault/Prometheus/Grafana and production auth/secrets posture.
2. Goal-run audit/event persistence should be promoted from file-backed verifier artifacts to DB-backed audit/event rows.
3. The north-star benchmark is still deterministic smoke coverage; it needs real baseline comparisons and repeated multi-domain evaluation before it measures capability expansion.
4. Some live web/source discovery checks still fail closed under network/API limits, which is safer than synthetic fallback but not full live web capability.
5. Specialist workers are still launched through local Flask development servers in tests; production worker serving needs a non-dev runtime before production claims.

## Developer Next Commands

```bash
make verify-system-offline
make verify-system-native
make doctor
make run-best-effort
cd backend && DATABASE_URL=<local-native-postgres-dsn> npm test -- --runInBand --forceExit
```
