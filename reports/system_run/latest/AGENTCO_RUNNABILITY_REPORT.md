# AgentCo Runnability And Goal-Fit Report

## Executive Verdict

**PARTIALLY_RUNNABLE**

AgentCo is runnable in meaningful slices, but not as one clean full-stack system from a fresh local environment. The TypeScript backend builds, tests, and starts. The frontend tests, lints, and builds. Native Postgres is reachable and already contains the expected AgentCo schema. A live OpenAI-compatible call using `.codex.env` works. A live goal-oriented verification run completed with OpenAI reasoning, deterministic policy control, prediction registration, legacy resolution/scoring, trust update, event/audit/decision records, and memory write.

The system is not fully clean-checkout runnable here because Docker infrastructure is unavailable, the documented Python migration path fails due missing `psycopg2`, and the default `python3` package installer is broken by a local Python 3.14 `pyexpat` linkage issue. The primary prediction ledger can register predictions, but direct resolution as user `agentco` is correctly blocked by the database role guard requiring `resolution_service`.

Commit verified: `e53f018140a19318d0df2b42131b0f4b81c6e2f4`

## Environment Summary

| Item | Result |
|---|---|
| Repository | `/Users/Zet/Desktop/Agentco` |
| Git status at start | clean |
| Node | `v24.17.0` |
| npm | `11.13.0` |
| Python default | `3.14.4` |
| Python with pytest | `/Users/Zet/anaconda3/bin/python3.13`, `3.13.9` |
| Docker CLI | present |
| Docker daemon | unavailable |
| Postgres | native `localhost:5432`, reachable |
| Env file | `.codex.env` present; `codex.env` absent |
| OpenAI variable | repo uses `LLM_API_KEY`; `OPENAI_API_KEY` absent |

No secret values were printed or committed.

## Runtime Orchestration

AgentCo now has an explicit doctor/orchestration layer with runtime modes:

`production`, `local_full`, `local_native`, `offline_fixture`, `ci_smoke`, and `degraded`.

Latest local-native doctor result:

| Field | Value |
|---|---|
| Selected runtime mode | `local_native` |
| Can continue | `true` |
| Safe next command | `make run-best-effort` |
| Run type | `mixed`: real Postgres/OpenAI with explicit local fallbacks for missing optional infra |

Service/fallback behavior observed in this environment:

| Service | Status | Safe behavior |
|---|---|---|
| Docker daemon | `blocked` | Select `local_native`; do not require Docker when native Postgres is healthy |
| Postgres | `real` | Use native Postgres for DB writes |
| Core DB schema | `real` | Continue |
| Kafka | `missing` | Use explicit in-process event bus fallback outside production |
| Redis | `missing` | Use explicit memory cache fallback outside production |
| Vault | `missing` | Use explicit env secret provider fallback outside production |
| Prometheus | `missing` | Write JSON metrics artifacts |
| Grafana | `missing` | Skip dashboard UI; keep metrics JSON |
| OpenAI | `real` | Live LLM calls allowed in `local_native` |
| Resolution service | `real` | Primary ledger resolution enabled |
| Sensitive route auth | `real` | `/api/overrides` unauthenticated probe returns 401 |

Artifacts:

- `doctor_report.json`
- `doctor_report.md`
- `docs/runtime_capability_contract.md`

## Commands Executed

| Command | Exit | Evidence |
|---|---:|---|
| `pwd; git status --short; git rev-parse HEAD; find ...` | 0 | `recon_summary.json` |
| `python3 --version; node --version; npm --version; docker --version; docker compose version; psql --version` | 0 | `tool_versions.txt` |
| `docker compose ps; docker ps` | nonzero | `infra_logs.txt` |
| `pg_isready ...; psql ... select current_database()` | 0 | `db_connectivity.txt` |
| `cd backend && npm run db:migrate` | 1 | `migration_run.txt` |
| `cd backend && npx tsc --noEmit` | 0 | `backend_tsc_noemit.log` |
| `cd backend && npm test -- --runInBand --forceExit` | 0 | `backend_test.log` |
| `cd backend && npm run build` | 0 | `backend_build.log` |
| `node dist/server.js` plus endpoint probe | 0 for server/probe | `backend_logs.txt`, `backend_endpoint_probe.json` |
| `cd frontend && npm test` | 0 | `frontend_test.log` |
| `cd frontend && npm run lint` | 0 | `frontend_lint.log` |
| `cd frontend && npm run build` | 0 | `frontend_build.log` |
| `python3 -m pip install -r agents/requirements.txt` | 1 | `python_dependency_install.log` |
| `python3 -m pytest calibration runtime agents tests evals -q` | 1 | `python_runtime_tests.log` |
| `python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q` | 0 | `verify_goal_run_tests_py313.log` |
| `python3 scripts/verify_openai_connectivity.py` | 0 | `openai_connectivity.json` |
| `python3 scripts/verify_agentco_goal_run.py` | 0 | `goal_run.json`, `goal_run.md` |
| `cd backend && npx ts-node scripts/civilization-free-run.ts --mode fixture` | 0 | `civilization_free_run_fixture.log` |

## Infrastructure Results

| Service | Result | Notes |
|---|---|---|
| Docker Compose stack | broken here | Docker daemon unavailable: `Cannot connect to the Docker daemon...` |
| Postgres | real/running | Native Postgres accepted connections on `localhost:5432` |
| Redis | unavailable | `redis-cli` absent; port not verified as running |
| Kafka | unavailable | port `9092` closed; Docker unavailable |
| Vault | unavailable | port `8200` closed |
| Prometheus | unavailable | port `9090` closed |
| Grafana | unavailable | port `3005` closed |

## Migration Results

The documented backend migration command failed:

```text
cd backend && npm run db:migrate
ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary
exit_code=1
```

The root cause is not only the missing package. `python3 -m pip install -r agents/requirements.txt` also fails before dependency resolution because Python 3.14 cannot load `pyexpat`:

```text
ImportError: ... pyexpat.cpython-314-darwin.so ... Symbol not found: _XML_SetAllocTrackerActivationThreshold
```

Schema verification against native Postgres succeeded. `db_schema_summary.txt` shows 223 public tables and core tables including `prediction_ledger`, `prediction_resolutions`, `predictions`, `decision_log`, `event_history`, `autonomy_memory`, `eval_runs`, `override_queue`, and `active_artifacts`.

## Backend Results

| Check | Result |
|---|---|
| TypeScript no-emit | passed, 2.42s |
| Default Jest | passed: 25 suites passed, 4 skipped; 154 tests passed, 26 skipped |
| Build | passed |
| Server start | passed on port `3101` |
| Health endpoint | `GET /health` returned 200 |

Endpoint probe findings:

| Endpoint | No Auth | With Dev Auth | Assessment |
|---|---:|---:|---|
| `/health` | 200 | 200 | OK |
| `/api/protected-surfaces/check?field=foo` | 401 | 200 | protected as expected |
| `/api/ensemble/experts` | 401 | 403 | auth and scope checks active |
| `/api/civilization/solve` | 400 | 400 | route exists, validates input |
| `/api/overrides` | 401 | 200 | protected after fix |

## Frontend Results

| Check | Result |
|---|---|
| `npm test` | passed: civilization dashboard surface check |
| `npm run lint` | passed with one warning |
| `npm run build` | passed; 18 static routes generated |

Warning:

```text
./src/app/audit/page.tsx
React Hook useEffect has a missing dependency: 'load'
```

Dashboard routes compiled for audit, events, override, performance, dashboard, and civilization pages. This proves frontend buildability, not live real-time data freshness.

## Python Runtime Results

Default Python runtime is not cleanly runnable:

| Check | Result |
|---|---|
| `python3 -m pip install -r agents/requirements.txt` | failed due Python 3.14 `pyexpat` linkage |
| `python3 -m pytest calibration runtime agents tests evals -q` | failed: `No module named pytest` |
| `python3.13 -m pytest tests/test_verify_agentco_goal_run.py -q` | passed: 6 tests |

The repository has Python tests and scripts, but the default machine Python cannot install or run them as configured.

## OpenAI Connectivity

`scripts/verify_openai_connectivity.py` loaded `.codex.env`, used `LLM_API_KEY`, and called the OpenAI-compatible chat completions endpoint.

Result: **success**

| Field | Value |
|---|---|
| Model | `gpt-4o-mini` |
| Latency | 2494.48 ms |
| Tokens | 73 total |
| Output | JSON response with `status`, `claim`, `confidence` |

Artifact: `openai_connectivity.json`

## Full Goal-Oriented Run

`scripts/verify_agentco_goal_run.py` ran the synthetic vendor-risk scenario.

Result: **completed successfully**

| Step | Evidence |
|---|---|
| Agent task intake | synthetic task embedded in `goal_run.json` |
| Evidence parsing | validation requires `ev1` and `ev2`, rejects unknown IDs |
| Prediction pre-registration | `prediction_ledger_insert` succeeded |
| OpenAI reasoning | `raw_reasoning` from `gpt-4o-mini`, 565 total tokens |
| Structured output validation | all final validation checks passed |
| Confidence extraction | final confidence `0.6` |
| Trust-adjusted confidence | `0.4617` |
| Policy/evidence checks | passed, including no breach conflation |
| Audit/event records | `decision_log`, `event_history`, `autonomy_audit_events` inserts succeeded |
| Human escalation | final decision `escalate`, `human_escalation_required=true` |
| Resolution/scoring | primary `prediction_ledger` resolution update and legacy `prediction_resolutions` insert succeeded, Brier `0.16` |
| Learning/trust update | `trust_scores` and `autonomy_memory` inserts succeeded |

Important nuance: the raw LLM output was not accepted directly. It escalated correctly but returned `risk_level=high` and placed forbidden phrases in `unsupported_claims`. The verification harness applied a deterministic policy controller that produced the final evidence-governed result while preserving the raw output. This is evidence-governed behavior, not just answer generation.

Follow-up fix status: `FIX_MODULE_RUNNABILITY.md` records that the verifier now uses a separate `resolution_service` connection for primary ledger resolution. The final live run in `goal_run.json` has `prediction_ledger_resolution_update: ok`.

## Civilization Free-Run

`npx ts-node scripts/civilization-free-run.ts --mode fixture` passed. It produced a no-goal free-run report:

```text
weaknesses: weak_domain, unpromoted_knowledge
claims: processed=1 promoted=1 blocked=0
queue: governance_requests=2
predictions: 1
```

This is a real vertical slice in fixture mode. It is not proof of unrestricted autonomous civilization-scale operation.

## Primary Questions

| Question | Answer |
|---|---|
| 1. Runnable from clean checkout? | partial. Node backend/frontend are runnable after dependencies, but Python install/migrations are blocked here and Docker daemon is unavailable. |
| 2. Backend start? | yes. `node dist/server.js` started and health returned 200. |
| 3. Frontend start/build? | build yes. Dev server was not necessary for proof; build/test/lint passed. |
| 4. Database/infrastructure start? | native Postgres yes. Docker Compose stack no. Redis/Kafka/Vault/Prometheus/Grafana unavailable. |
| 5. Migrations apply? | yes after fix. `npm run db:migrate` now uses the backend TypeScript runner and completed successfully; all current migrations were skipped as already applied. |
| 6. One real agent task end-to-end? | yes for the added goal-run harness: OpenAI + policy controller + DB trail. Also fixture free-run works. |
| 7. OpenAI call via env? | yes using `LLM_API_KEY` from `.codex.env`. |
| 8. Calibration ledger register predictions? | yes, `prediction_ledger_insert` succeeded. |
| 9. Resolution/scoring run? | yes after fix. primary ledger resolution passed through `resolution_service`; legacy resolution/scoring also succeeded. |
| 10. Trust/controller update trusted confidence? | yes. policy controller produced final decision; `trust_scores_insert` succeeded with trusted confidence `0.4617`. |
| 11. Audit/event records generated? | yes. `event_history`, `decision_log`, `autonomy_audit_events`, and `autonomy_memory` writes succeeded. |
| 12. Evidence-governed not simulated? | yes in the goal run: final decision was constrained by evidence IDs, policy checks, hallucination traps, and DB records. |
| 13. Learning/self-improvement safely? | partial. memory/trust writes exist; recent self-improvement gates exist, but autonomous safe improvement is not fully proven by this run. |
| 14. Expands across domains? | partial/aspirational. vendor-risk cross-domain schema worked; broad cross-domain transfer metrics are not measured. |
| 15. Real/partial/simulated/broken/missing? | see matrices below. |

## Evidence Governance Matrix

| Capability | Status | Evidence |
|---|---|---|
| Evidence objects | real | goal task evidence IDs and backend tests |
| Source independence | partial | enforced in some services; not globally verified |
| Auditability | real | decision/event/autonomy audit rows written |
| Signed event envelopes | partial | event tables exist; signature path not proven |
| Immutable logs | real/partial | `decision_log` has no-update/no-delete triggers |
| Source-resolution separation | real | ledger resolution blocked unless `resolution_service` |
| Circular verification prevention | partial | not fully exercised |
| Provenance completeness | partial | goal run has evidence IDs; not universal |

## Calibration-Driven Operation Matrix

| Capability | Status | Evidence |
|---|---|---|
| Stated confidence | real | OpenAI/final goal output confidence |
| Trusted confidence | real | computed and inserted into `trust_scores` |
| Prediction ledger | real | `prediction_ledger_insert` |
| Pre-registration | real | ledger insert before synthetic resolution path |
| Scoring | partial | legacy Brier path worked; main ledger resolution blocked by role |
| Brier/log/ECE | partial | Brier/log/ECE values inserted into `trust_scores` |
| Reliability curves | partial | code exists, not exercised in this run |
| Trust updates | real | `trust_scores_insert` |
| Abstention/escalation | real | final decision escalated |
| Calibration dashboards | partial | frontend routes build; live data not verified |

## AI Civilization Substrate Matrix

| Capability | Status | Evidence |
|---|---|---|
| Multiple agents | partial | ensemble initializes; route scope protected |
| Agent roles | partial | free-run and services refer to roles |
| Inter-agent communication | partial | event history exists; Kafka unavailable |
| Shared memory | real | `autonomy_memory` write succeeded |
| Governance rules | real | policy controller and DB role guard |
| Override queue | partial/broken | endpoint returns data without auth |
| Audit log | real | audit/event/decision rows |
| Policy enforcement | real | protected surface auth, controller checks |
| Self-extension controls | partial | recent rollback/gating code, not fully run here |
| Resource/reserve controls | partial | schema/code present; not stress-tested |

## Continuous Learning Matrix

| Capability | Status | Evidence |
|---|---|---|
| Memory write/read path | partial | write succeeded; read-back not exercised |
| Feedback ingestion | partial | synthetic resolution and trust update |
| Score-based trust updates | real | `trust_scores` row inserted |
| Learning from resolved predictions | partial | memory lesson written from synthetic resolution |
| Regression tests from failures | partial | new harness tests added |
| Eval-driven improvement loop | partial | eval tables exist; not run end-to-end |
| Safe self-modification | partial | prior rollback/gating code; not fully verified here |
| Release gates | partial | build/test gates pass; not production release gate |

## Capability Expansion Matrix

| Capability | Status | Evidence |
|---|---|---|
| Domain-agnostic task schema | partial | vendor-risk scenario worked |
| Model adapter abstraction | partial | OpenAI-compatible env path works |
| Tool abstraction | partial | services/scripts exist; not uniformly verified |
| Benchmark/eval registry | partial | eval dirs/tables exist; not fully run |
| Domain-specific agents | partial | finance/vendor/free-run slices, not comprehensive |
| General planning capability | partial | fixture free-run proposes internal goal |
| Multi-domain evals | partial/missing | not measured in this run |
| Baseline comparison | missing | no cross-domain F1/skill-reuse metric produced |

## Safety And Governance Matrix

| Capability | Status | Evidence |
|---|---|---|
| Secrets handling | real | key presence checked without printing values |
| API auth | partial | some protected routes work |
| RBAC/scoped permissions | real/partial | `/api/ensemble/experts` returned 403 without scope |
| Human override | partial | queue exists; unauthenticated read is a bug |
| No timeout auto-approval | not proven | not exercised |
| Tool sandboxing | partial | not broadly verified |
| Dangerous action prevention | partial | ledger role guard and policy controller |
| Auditability | real | rows written |
| Production fail-closed checks | partial | some routes fail closed, `/api/overrides` does not |

## Real vs Simulated

| Area | Classification |
|---|---|
| Backend build/test/start | real |
| Frontend build/test/lint | real |
| Native Postgres connectivity/schema | real |
| OpenAI connectivity | real |
| Goal-run LLM call | real |
| Goal-run final policy controller | real deterministic guard |
| Prediction ledger registration | real |
| Legacy resolution/scoring | real |
| Trust score insert | real |
| Audit/event/decision records | real |
| Offline goal-run mode | simulated and clearly marked |
| Docker Compose infra | broken/unavailable |
| Main ledger resolution update | real |
| Kafka-dependent behavior | missing in this environment |
| Broad cross-domain transfer | mostly aspirational |

## Broken Pieces And Root Causes

| Issue | Root Cause | Suggested Fix |
|---|---|---|
| Docker stack cannot start | Docker daemon unavailable | Start Docker Desktop/daemon or document native-infra path |
| Python migration runner fails | `psycopg2` missing under default Python | Backend `npm run db:migrate` now uses the TypeScript runner; keep Python runner only as optional/legacy or pin its env |
| `pip install` fails | local Python 3.14 `pyexpat` linkage | Use Python 3.13 env, repair Homebrew Python/libexpat, or commit a supported venv/uv workflow |
| Default Python tests fail | `pytest` absent under Python 3.14 | Use Python 3.13 or install deps after fixing pip |
| `/api/overrides` was readable without auth | route lacked protection | Fixed: read routes now require `governance:mutate` |
| Main ledger resolution update was blocked | verifier used app DB user instead of `resolution_service` | Fixed: verifier uses separate resolution-service DSN |
| Live LLM raw output not fully compliant | model used high risk and unsupported-claim phrasing | Keep controller; optionally add stricter structured schema/retry |

## Minimal Fixes

1. Pin and document a working Python version, preferably Python 3.13 here, for broad Python tests and optional Python scripts.
2. Add a root dependency workflow (`requirements.txt`, `uv.lock`, or equivalent) for Python runtime/test dependencies.
3. Document native Postgres mode separately from Docker Compose mode.

## Larger Architecture Gaps

1. Cross-domain transfer is still not measured with a north-star metric such as F1 delta or skill reuse.
2. Kafka/event bus infrastructure is configured but unproven in this environment.
3. The civilization layer has a working fixture/free-run slice, but not a fully autonomous, continuously operating, resource-bounded society.
4. Learning is present as memory/trust updates, but not yet a closed eval-driven self-improvement release loop.
5. Frontend pages build, but live dashboard data freshness and RBAC coverage need deeper verification.

## Recommended Next Phase

Fix the local run contract first: Python environment pinning, migration dependency path, authenticated override reads, and a documented `resolution_service` verifier. After that, the next high-leverage product goal is a real cross-domain transfer benchmark that compares baseline vs learned behavior and writes results into the calibration/trust substrate.
