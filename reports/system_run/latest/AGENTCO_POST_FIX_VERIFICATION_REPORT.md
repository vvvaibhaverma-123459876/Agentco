# AgentCo Post-Fix Verification Report

Date: 2026-06-25

## Final Verdict

`RUNNABLE_LOCAL_NATIVE`

This is not a clean production/full-stack verdict. The verified runnable path is local-native with real native Postgres, real backend/frontend builds, real OpenAI connectivity, real resolution-service role connectivity, and explicit fallbacks for missing Redis/Kafka/Vault/Prometheus/Grafana.

The repo is also `RUNNABLE_OFFLINE_FIXTURE`: the offline fixture path completes without external services and is explicitly marked simulated.

## Verified Fixes

| Area | Result | Evidence |
|---|---|---|
| Python 3.13 runtime | Pass | `make python-check`: Python 3.13.9, `41 passed` |
| Runtime modes | Pass | `runtime/orchestration/modes.py`; orchestration tests `7 passed` |
| Service doctor | Pass | `make doctor`: selected `local_native`, `can_continue=true` |
| Fallback orchestration | Pass | `make run-best-effort`: selected `local_native`, completed live goal run |
| Offline fixture mode | Pass | `make verify-system-offline`: `13 passed` |
| Native migration verification | Pass | `make verify-migrations-native`: Postgres real, core schema real |
| Resolution-service path | Pass | `make verify-resolution-service`: service role real, trigger guard proven |
| Override route auth | Pass | unauthenticated `GET /api/overrides` returned `401` |
| Backend build | Pass | `cd backend && npm run build` |
| Frontend smoke/lint/build | Pass | `npm test`, `npm run lint`, `npm run build` |
| OpenAI connectivity | Pass | `gpt-4o-mini`, latency 1676 ms, 61 tokens |
| Live goal run | Pass | `simulated=false`, decision `escalate`, validation score `1.0` |
| North-star smoke benchmark | Pass | 4 domains, deterministic aggregate `1.0`; marked smoke/skeleton |

## Not Fully Verified

| Area | Status | Detail |
|---|---|---|
| Full backend Jest suite | Failed | `19 failed, 4 passed`; existing tests still have schema/env/network drift |
| Production mode | Blocked | Production requires real Vault/Redis/Kafka/observability and no fallbacks |
| Real cross-domain general intelligence | Not proven | North-star benchmark is deterministic smoke/skeleton only |
| DB audit writes from goal-run | Partial | Goal-run writes file-backed audit/event report; not a DB audit-log integration |

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

Disabled capabilities: none in the final local-native doctor report. These are still fallback capabilities, not real infrastructure.

## Migration Verification

`reports/system_run/latest/migration_verification.json`:

| Check | Result |
|---|---|
| Postgres connectivity | `real` |
| Migration dependency | `real` (`ts-node src/db/migrate.ts`) |
| Core schema | `real` |
| Required tables | `decision_log`, `override_queue`, `prediction_ledger` |

## Resolution-Service Verification

`reports/system_run/latest/resolution_service_verification.json`:

| Check | Result |
|---|---|
| resolution_service path | `success` |
| unauthorized resolution guard | `success` |
| guard proof | live trigger metadata enforces `resolution_service` current_user for resolution writes |

## Override Auth Verification

Backend was started with:

```text
env PORT=3101 DATABASE_URL=<redacted local Postgres DSN> node dist/server.js
```

Probes:

| Endpoint | Result |
|---|---|
| `GET /health` | `200 OK` |
| `GET /api/overrides` without API key | `401 Unauthorized` |

This fixes the prior governance issue where read access entered the handler without auth.

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
| goal latency | about 2.5 s |
| audit/event records | file-backed event trail recorded |

The run is evidence-governed at the verifier level: it requires `ev1` and `ev2`, rejects unsupported SOC 2 Type II confirmation, rejects breach conflation, requires missing SOC 2 Type II report, signed DPA, and subprocessors, and validates confidence bounds.

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
make doctor
make doctor-offline
make run-offline-fixture
make run-best-effort
make verify-system-offline
make verify-system-native
make north-star-smoke
python3.13 -m pytest runtime/orchestration/tests -q
python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q
python3.13 -m pytest evals/north_star_cross_domain/tests -q
python3 scripts/verify_openai_connectivity.py
python3 scripts/verify_agentco_goal_run.py
cd backend && npm run build
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run build
```

Failed:

```text
cd backend && npm test -- --runInBand --forceExit
```

Failure summary: broad pre-existing backend test drift remains. Observed classes include network-dependent real web tests under restricted network, `/tmp/.s.PGSQL.5433` DB socket defaults in integration tests, missing `axios`, TypeScript `it.skipIf` misuse, source discovery fixtures returning no sources, and reflection-test expectation drift. This blocks a clean full-stack/production verdict but does not block the verified local-native runnable path.

## Performance Summary

| Metric | Latest observed |
|---|---:|
| OpenAI connectivity latency | 1676 ms |
| OpenAI connectivity tokens | 61 |
| Goal-run latency | about 2544 ms |
| Goal-run tokens | about 353 |
| Frontend build | completed in about 11 s |
| Backend build | completed in about 3 s |
| Python runtime tests | 41 tests in about 0.4 s |
| Offline verification tests | 13 tests in about 1.0 s |

## Remaining Blockers

1. Fix or split the backend Jest suite so default local tests do not require unavailable network, wrong DB socket paths, missing packages, or stale expectations.
2. Add a DB-backed goal-run audit/ledger write path beyond the current file-backed verifier event trail.
3. Replace local fallbacks with real Kafka/Redis/Vault/observability before any production claim.
4. Expand the north-star benchmark from deterministic smoke/skeleton to real comparative multi-domain evaluation.
5. Add production doctor evidence for auth, secrets, observability, and fail-closed deployment checks.

## Developer Next Commands

```bash
make verify-system-offline
make verify-system-native
make doctor
make run-best-effort
cd backend && npm test -- --runInBand --forceExit
```
