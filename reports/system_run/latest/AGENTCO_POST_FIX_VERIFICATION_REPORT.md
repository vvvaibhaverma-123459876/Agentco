# AgentCo Post-Fix Verification Report

**Date:** 2026-06-25  
**Commit verified:** 42a5e3bdea4b6808b1ad119ab7189ec2aa49a0e3  
**Verifier:** Claude Code fork (claude-opus-4-8)

---

## 1. Final Verdict

**`RUNNABLE_WITH_FALLBACKS`**

Agentco is runnable locally with explicit, safe fallbacks. It is NOT a clean full-stack run (Docker daemon unavailable during prior perf summary; Redis/Kafka/Vault/Prometheus/Grafana ports not reachable). However, the runtime doctor correctly detects and declares fallbacks; offline fixture and best-effort modes both complete successfully; the full DB schema is present and live; live OpenAI connectivity is verified; backend and frontend build/test cleanly.

---

## 2. Run Type

- **offline_fixture**: PASS — `make run-offline-fixture` → `success=true, latency=459ms, mode=simulated_offline`
- **local_native (best-effort)**: PASS — `make run-best-effort` → `success=true, latency=2943ms, mode=live_openai`
- **verify-system-offline**: PASS — `make verify-system-offline` → `success=true, mode=simulated_offline`
- **Full clean stack (Docker Compose up)**: NOT verified — Docker daemon reported unavailable during performance_summary capture; note: doctor NOW reports `docker_daemon: real` so daemon may have recovered between sessions.

---

## 3. Fixes Verified

| Fix | Verified? | Evidence |
|---|---|---|
| Runtime doctor (offline + local_native modes) | ✅ YES | `make doctor-offline` + `make doctor` both complete; JSON report present |
| Fallback orchestration (Redis/Kafka/Vault/Prometheus explicit fallbacks) | ✅ YES | doctor_report.json `fallbacks_used` lists all 5 with named fallback strategy |
| Override route auth (`GET /api/overrides` → 401 unauth, 200 auth) | ✅ YES | backend_endpoint_probe.json: unauthenticated=401, authenticated=200 |
| Scoped auth on sensitive routes (`/api/ensemble/experts` → 403 wrong scope) | ✅ YES | probe: `lacks scope trust:read` = 403 as expected |
| Resolution service path (login verified by doctor) | ✅ YES | doctor: `resolution_service: real, "resolution_service login works"` |
| Native Postgres + core schema | ✅ YES | doctor: `postgres: real`, `core_db_schema: real` (prediction_ledger, decision_log, event_history, trust_scores) |
| Migration runner present | ✅ YES | doctor: `migrations: real`, `migration_dependencies: real` |
| Live OpenAI connectivity | ✅ YES | openai_connectivity.json: `success=true, latency=1206ms, model=gpt-4o-mini` |
| Goal run (offline) | ✅ YES | `success=true, mode=simulated_offline` |
| Goal run (live LLM) | ⚠️ PARTIAL — see §11 | goal_run.json shows `error: missing OPENAI_API_KEY/LLM_API_KEY` for full goal run (env not set for that script path) |
| Python orchestration tests (py3.13) | ✅ YES | 8 passed in 4.74s |
| Goal run tests (py3.13) | ✅ YES | 6 passed in 0.02s |
| Backend Jest tests | ✅ YES | 25 suites passed, 156 tests passed, 26 skipped, 4 suites skipped |
| Frontend lint | ✅ YES (warning only) | 1 ESLint warning (missing useEffect dep), not an error |
| Frontend build | ✅ YES | Static Next.js build completed cleanly |

---

## 4. Doctor — Runtime Mode and Fallbacks

**Selected mode (offline):** `offline_fixture`  
**Selected mode (default):** `local_native`  
**can_continue:** `true`  
**Required fixes:** None  
**Disabled capabilities:** None  

**Fallbacks declared:**
| Service | Status | Fallback |
|---|---|---|
| redis | missing | memory_cache |
| kafka | missing | file_event_log |
| vault | missing | env_secret_provider |
| prometheus | missing | json_metrics_writer |
| grafana | missing | metrics_json_only |

---

## 5. Migration Verification

- `make verify-migrations-native`: **target does not exist in Makefile** — this specific target was specified in the brief but was never implemented. Doctor covers migration readiness via `migrations: real` and `core_db_schema: real`.
- Native Postgres reachable: YES (`agentco|agentco` at localhost:5432)
- Core schema tables present: `prediction_ledger`, `decision_log`, `event_history`, `trust_scores`
- No secrets printed during verification.
- **Classification: COVERED by doctor, no standalone migration verifier.**

---

## 6. Resolution Service Verification

- `make verify-resolution-service`: **target does not exist in Makefile**
- Doctor reports: `resolution_service: real` — `"resolution_service login works"`
- No `resolution_service_verification.json` report written.
- **Classification: `blocked` — no standalone resolution-service verifier script. Doctor confirms login only.**

---

## 7. Override Route Auth

- `GET /api/overrides` unauthenticated: **401** `{"error":"valid service key required"}` ✅
- `GET /api/overrides` authenticated: **200** ✅
- `GET /api/overrides/overdue` unauthenticated: **401** ✅
- `GET /api/protected-surfaces/check` unauthenticated: **401** ✅
- `GET /api/ensemble/experts` authenticated (wrong scope): **403** `lacks scope trust:read` ✅
- **GOVERNANCE GATE: PASSED.** Unauthenticated access to sensitive routes correctly returns 401.

---

## 8. North-Star Cross-Domain Benchmark

- `make north-star-smoke`: **target does not exist in Makefile**
- `evals/north_star_cross_domain/`: **directory does not exist**
- `results/north_star_cross_domain/`: **directory does not exist**
- **RESULT: NOT IMPLEMENTED.** The north-star smoke benchmark was specified in the brief but has no corresponding code, Makefile target, or results directory. This is a gap.

---

## 9. OpenAI Live Goal-Run

- `verify_openai_connectivity.py`: **SUCCESS** — `success=true, latency=1258ms, model=gpt-4o-mini`, token usage recorded, no key printed
- `verify_agentco_goal_run.py` (offline): **SUCCESS** — `success=true, mode=simulated_offline`
- Full live goal run (`goal_run.json`): **FAILED** — `error: missing OPENAI_API_KEY/LLM_API_KEY`. The connectivity script finds the key; the goal-run script does not — env var name mismatch between scripts (connectivity uses `LLM_API_KEY`, goal-run uses `OPENAI_API_KEY`). The performance_summary shows a prior successful live goal run with 565 tokens used.
- **`simulated=false`** confirmed for connectivity check. Goal run live path: blocked by env var naming inconsistency.

---

## 10. Python Tests

| Suite | Command | Result |
|---|---|---|
| Orchestration tests | `python3.13 -m pytest runtime/orchestration/tests -q` | **8 passed** |
| Goal run tests | `python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q` | **6 passed** |

---

## 11. Backend Tests

```
Test Suites: 4 skipped, 25 passed, 25 of 29 total
Tests:       26 skipped, 156 passed, 182 total
Time:        4.057s
```
- `protected-surfaces.test.ts`: PASS — enforcer loads 4 surfaces from policy.py
- `override-queue.test.ts`: PASS
- `audit-log.test.ts`: PASS
- 4 suites skipped (not failures)

---

## 12. Frontend Tests/Build

| Step | Result |
|---|---|
| `npm run lint` | WARN (1 missing useEffect dep) — not an error |
| `npm run build` | **PASS** — full static Next.js build |
| `npm test` | Not run in this session; prior report shows passing |

---

## 13. Performance Summary (from existing report)

- Backend TSC: 2.42s
- Backend Jest: 5.5s
- Backend build: 2.5s
- Frontend lint: 2.69s
- Frontend build: 10.41s
- OpenAI connectivity: 2.49s
- Doctor offline: 3.6s
- Run offline fixture: 4.03s
- Run best-effort local_native: 20.32s
- Orchestration tests: 7.17s
- Native Postgres: healthy
- Docker daemon: previously unavailable; now reporting real

---

## 14. Remaining Blockers

| Blocker | Severity | Notes |
|---|---|---|
| `make verify-migrations-native` missing | Low | Doctor covers it; standalone target not needed if doctor is the verification path |
| `make verify-resolution-service` missing | Medium | No standalone verifier; doctor only confirms login |
| `make north-star-smoke` missing | High | North-star cross-domain benchmark does not exist anywhere in the repo |
| `evals/north_star_cross_domain/` missing | High | No four-domain benchmark code |
| `results/north_star_cross_domain/` missing | High | No results directory or scoring output |
| Goal run live env mismatch | Medium | `verify_agentco_goal_run.py` looks for `OPENAI_API_KEY`; key is stored as `LLM_API_KEY` |
| Redis/Kafka/Vault not running | Low | Fallbacks active and explicit; not a blocker for local dev |
| 4 skipped Jest suites | Low | Review if intentional |
| `make verify-system-native` missing | Low | Makefile has no `verify-system-native` target |
| Protected surface enforcer integration | Medium | Per prior audit (civilization_audit_phase_a): enforcer is built and tests pass but may still be orphaned from runtime paths — tests pass in isolation |

---

## 15. Exact Next Commands for a Developer

```bash
# 1. Start here — offline smoke
make doctor-offline
make run-offline-fixture

# 2. Full local run (needs Postgres running)
make doctor
make run-best-effort

# 3. Fix live goal-run env var mismatch
# Edit scripts/verify_agentco_goal_run.py to also check LLM_API_KEY
export OPENAI_API_KEY=$LLM_API_KEY
python3 scripts/verify_agentco_goal_run.py

# 4. North-star benchmark (does not exist — must be built)
mkdir -p evals/north_star_cross_domain/tests
mkdir -p results/north_star_cross_domain
# Then implement: vendor_risk, medical-triage-safe-info, financial-risk-disclosure, code-change-risk-review domains

# 5. Verify resolution service standalone
# Create: scripts/verify_resolution_service.py
# Create Makefile target: verify-resolution-service

# 6. Full test pass
python3.13 -m pytest runtime/orchestration/tests evals/ tests/ -q
cd backend && npm test -- --runInBand --forceExit
cd frontend && npm run build

# 7. Wire protected-surface enforcer into a real runtime path and add integration test
```

---

## Summary

Agentco is **`RUNNABLE_WITH_FALLBACKS`**. Both major fix phases (runnability/governance hardening + resilient runtime doctor/fallback orchestration) are committed and produce working outcomes. The override route auth governance gate passes. Native Postgres and core schema are healthy. Live OpenAI connectivity works. Offline fixture and best-effort modes complete successfully. The north-star cross-domain benchmark is the largest unimplemented item remaining.
