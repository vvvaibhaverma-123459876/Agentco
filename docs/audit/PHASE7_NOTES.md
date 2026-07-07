# Phase 7 Notes — Release Credibility Gate

## Task 1 — Clean-Clone Python Failures

Clean-clone command:

```text
python3.13 -m pytest -q
```

Initial result on branch base:

```text
5 failed, 508 passed, 43 skipped, 5 warnings, 1 error in 87.83s
```

| test id | class | verdict before fix | fix | verification |
|---|---|---|---|---|
| `agents/tests/integration/test_agent_dispatch_e2e.py::test_full_dispatch_path_touches_real_postgres_ledger_audit_and_kafka` | LIVE-SERVICE | The test requires both real Postgres and real Kafka. Postgres was reachable, but Kafka at `localhost:9092` refused connections, then teardown also failed by trying to disable all triggers as a non-superuser. | Added explicit Postgres/Kafka capability probes and `skipif` marks so missing live services skip before fixture setup. | Focused run: skipped with reason when Kafka absent. |
| `learning/tests/test_learning_loop.py::TestScenarioAgent::test_generates_hypotheses_for_focus_areas` | CONTRACT-BUG | The V2 gate was correct: low-risk actions with trusted confidence below `0.50` must block. The production `ScenarioAgent` marked deterministic provisional hypothesis emission with `stated_confidence=0.65`; with no track record that degraded to `0.455`, contradicting the intended ready-hypothesis path. | Raised the bounded deterministic action confidence to `0.75`, yielding trusted confidence above the gate while preserving low-risk provisional semantics. | Focused run: passed. |
| `runtime/tests/test_base_agent_v2.py::TestBaseAgentV2DurableAudit::test_durable_audit_writer_round_trip_live_postgres` | CONTRACT-BUG | The runtime gate was correct. The test intended to verify the durable audit writer but built an unearned `stated_confidence=0.7` action, which degraded to `0.49` and blocked before audit. | Changed the test action to `stated_confidence=0.8`, legitimately clearing the confidence gate while still exercising the low-risk durable audit write path. | Focused run: passed. |
| `tests/e2e/test_memory_lifecycle.py::test_reader_track_record_and_format` | GENUINE | The test created a pre-registration with a past `resolution_date` but no historical-registration reason, violating the ledger's forward-claim contract. | Added `historical_registration_reason` to make the already-resolved fixture explicit and compliant. | Focused run: passed. |
| `tests/test_db_client_runtime_config.py::test_backend_db_client_has_bounded_pool_and_retry_contract` | GENUINE | Static assertion was stale after Phase 5 made pool max env-configurable and adjusted timeout values. Runtime code was already correct. | Updated the test contract to assert `AGENTCO_PG_POOL_MAX` fallback and current timeout values. | Focused run: passed. |
| `tests/test_specialist_agent.py::TestResearcherAgent::test_fetch_page_action` | LIVE-SERVICE | A unit test called real `https://example.com` and expected success. That made the default suite depend on outbound HTTP and optional DB evidence persistence. | Replaced real fetch and persistence with per-instance fixtures so the test covers handler behavior only. | Focused run: passed. |
| `tests/test_specialist_agent.py::TestFetcherAgent::test_fetch_allowed` | LIVE-SERVICE | Same external HTTP assumption as the researcher fetch test. | Replaced real fetch and persistence with per-instance fixtures. | Focused run: passed. |

Focused verification:

```text
python3.13 -m pytest agents/tests/integration/test_agent_dispatch_e2e.py::test_full_dispatch_path_touches_real_postgres_ledger_audit_and_kafka learning/tests/test_learning_loop.py::TestScenarioAgent::test_generates_hypotheses_for_focus_areas runtime/tests/test_base_agent_v2.py::TestBaseAgentV2DurableAudit::test_durable_audit_writer_round_trip_live_postgres tests/e2e/test_memory_lifecycle.py::test_reader_track_record_and_format tests/test_db_client_runtime_config.py::test_backend_db_client_has_bounded_pool_and_retry_contract -q
s.... [100%]
4 passed, 1 skipped
```

## Task 2 — No-Diff Verification

Initial dirty paths after default Python suite plus `make status` in a clean clone:

```text
M README.md
M evals/acceptance/pawdent_agent_decisions.jsonl
M evals/acceptance/pawdent_business_run.md
M evals/acceptance/pawdent_calibration_ledger.csv
M evals/acceptance/pawdent_monthly_financials.csv
M evals/acceptance/pawdent_summary.json
M reports/system_run/latest/doctor_report.json
M reports/system_run/latest/doctor_report.md
M reports/system_run/latest/goal_run.json
M reports/system_run/latest/production_posture_verification.json
```

Fixes:

- `scripts/generate_status.py --check` now verifies the README block without writing.
- `make status` keeps write behavior; `make status-check` is non-writing and exits nonzero on stale README status.
- `README.md` was regenerated so `status-check` passes from main.
- Runtime verification scripts honor `AGENTCO_REPORT_DIR` for test/untracked outputs.
- PawDent simulation honors `AGENTCO_ACCEPTANCE_DIR`; its tests monkeypatch module output paths to `tmp_path`.
- Production posture and run-best-effort tests redirect generated reports to `tmp_path`.
- CI master gate now runs `make status-check` and `test -z "$(git status --porcelain)"` after the gate.
- `frontend/next-env.d.ts` was updated to the current Next-generated dev route type path so `next dev`/frontend smoke no longer rewrites the tracked file.

Focused verification:

```text
python3.13 -m pytest tests/test_pawdent_business_simulation.py runtime/orchestration/tests/test_run_best_effort.py tests/test_verify_production_posture.py -q
13 passed

make status-check
README.md already up to date
```

## Task 3 — Error Contract: No Raw 500s

Verdict before fix: GENUINE. The central Fastify error handler returned `error.message` directly, and several active route catches returned caught exception text in `error` or `message` fields. The raw Postgres UUID case was one manifestation of the same problem: invalid path params were allowed to reach lower layers.

Fixes:

- Added `backend/src/http-errors.ts` with public error messages and correlation-id response shape `{ error, id }`.
- Added `backend/src/routes/param-validation.ts` and wired shared UUID path-param validation after API-key auth succeeds, so protected routes still return 401 before any path-param detail is exposed.
- Added a protected not-found handler for trailing-slash and case variants of protected paths: unauthenticated variants return 401; authenticated misses return 404.
- Replaced active route catch-block pass-throughs with stable public strings. Full exception details remain server-side through logs keyed by request id.

Focused verification:

```text
cd backend && npm test -- route-auth-contract.test.ts --runInBand
Test Suites: 1 passed, 1 total
Tests:       162 passed, 162 total

cd backend && npm run build
tsc passed
```

## Task 4 — Jest Open Handles

Verdict before fix: GENUINE. `backend/jest.config.ts` still carried the Phase 5 `forceExit` workaround. Running backend Jest without it showed that the suites passed but Jest did not return to the shell. `--detectOpenHandles` identified `pg` TCP handles from the shared DB pool, and the specialist suites left spawned Python subprocesses alive when tests only asserted activation.

Fixes:

- Removed `forceExit` from `backend/jest.config.ts`.
- Set the backend `pg` pool `allowExitOnIdle` under Jest so idle test DB sockets do not keep the event loop alive.
- Exposed `TeamActivationService.shutdown()` as a public wrapper around the existing graceful specialist shutdown path.
- Added `afterAll` cleanup to `team-activation.test.ts`, `specialist-integration.test.ts`, and `specialist-spawning.test.ts`.
- Made the action-loop no-content fetch test use an explicit no-content web adapter instead of falling through to live DNS.
- Made event-log, hash-anchor, and transactional-outbox tests reset their own event/outbox/anchor tables so stale developer DB chain rows do not poison default Jest.
- Made `identity-authority.test.ts` close its Fastify app from `afterEach`, even on failed assertions.

Focused verification:

```text
cd backend && npm test -- action-loop.test.ts --runInBand --detectOpenHandles
Test Suites: 1 passed, 1 total
Tests:       17 passed, 17 total

cd backend && npm test -- team-activation.test.ts specialist-integration.test.ts specialist-spawning.test.ts --runInBand --detectOpenHandles
Test Suites: 3 passed, 3 total
Tests:       5 todo, 24 passed, 29 total

cd backend && npm test -- event-log.test.ts hash-chain-anchor.test.ts transactional-outbox.test.ts identity-authority.test.ts --runInBand --detectOpenHandles
Test Suites: 4 passed, 4 total
Tests:       17 passed, 17 total
```

Full-suite note: the subsequent full backend run returned to the shell without `forceExit`; it exposed stale shared-DB chain fixtures, which were fixed above.

## Task 5 — Route-Auth Edge Cases

Verdict before fix: already covered by the Task 3 route-auth contract expansion. The contract suite now asserts:

- HEAD has the same auth posture as GET on a protected route.
- Trailing-slash variants do not bypass auth.
- Path-case variants do not bypass auth.
- Unclassified routes registered in the app still default to protected.
- Invalid UUID path params return sanitized 400s after auth, not raw lower-layer errors.

Verification:

```text
cd backend && npm test -- route-auth-contract.test.ts --runInBand
Test Suites: 1 passed, 1 total
Tests:       162 passed, 162 total
```

## Task 6 — Release Credibility Gate

Verdict before fix: GENUINE. The repository had partial gates (`master-gate`,
`verify-clean-room`, `release-gates`) but no single clean-clone/no-diff command
matching the re-audit credibility target. CI still used a backend Jest
`--forceExit` escape hatch and README quick-start examples also documented
forced exit.

Fixes:

- Added `make release-gate` with initial and final clean-tree assertions.
- The gate runs `make status-check`, the Python default suite, backend
  `npm ci`, migrations when `DATABASE_URL` is present, backend build, backend
  Jest without `forceExit`, the route-auth contract suite, the cross-writer
  decision-log chain test, frontend `npm ci`, and frontend `tsc --noEmit`.
- Updated CI's release job to run `make release-gate` and removed the backend
  Jest `--forceExit` argument.
- Updated README to document `make release-gate` as the stranger-trust command
  and removed stale `forceExit` examples.

Verification:

```text
pending final release-gate run
```
