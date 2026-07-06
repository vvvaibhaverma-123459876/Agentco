# Python Test Triage

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3.13 -m pytest -q --tb=short
```

Result: `16 failed, 478 passed, 46 skipped, 23 errors`.

## Phase 2 Regression Scope Flags

REGRESSION bucket tests touching governance, escalation, audit, or calibration paths:

- `evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_get_sample_count_with_track_record`
- `evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_execute_action_does_not_crash_for_agent_with_history`
- `evals/regression/test_audit_findings.py::TestHigh3DowngradePropagation::test_downgrade_propagates_to_consumers`
- `evals/regression/test_v2_regression.py::TestInvariant1_ImmutableLedger::test_resolution_write_once`
- `evals/regression/test_v2_regression.py::TestInvariant10_GroundTruthExternal::test_internal_resolution_source_rejected`
- `evals/regression/test_v2_regression.py::TestSeededFalseBeliefRegression::test_seeded_false_belief_cannot_reach_reality_validated`

These are not collection problems. They are calibration regression tests still creating backdated registrations after the ledger started enforcing future `resolution_date` unless `historical_registration_reason` is provided.

## Bucket Counts

| bucket | count |
|---|---:|
| LIVE-SERVICE | 25 |
| STALE | 8 |
| REGRESSION | 6 |
| COLLECTION | 0 |

## Failure And Error Rows

| test id | error summary | bucket | evidence | notes |
|---|---|---|---|---|
| `agents/tests/integration/test_tool_execution_real.py::test_permitted_tool_executes_and_writes_real_row` | `psycopg2.OperationalError` connecting to localhost Postgres | LIVE-SERVICE | `agents/core/tools/handlers.py:29` calls `psycopg2.connect(_DB_URL)`; pytest output shows `connect EPERM localhost:5432` | Should be skipped when real DB is unavailable. |
| `agents/tests/integration/test_tool_execution_real.py::test_unpermitted_tool_is_denied_before_handler_runs` | `psycopg2.OperationalError` connecting to localhost Postgres | LIVE-SERVICE | `agents/tests/integration/test_tool_execution_real.py:34` calls `_conn()`; output shows `connect EPERM localhost:5432` | Should be skipped when real DB is unavailable. |
| `agents/tests/integration/test_tool_execution_real.py::test_denial_via_base_agent_writes_real_audit_entry` | `psycopg2.OperationalError` connecting to localhost Postgres | LIVE-SERVICE | test calls `_count_denied()` -> `_conn()`; output shows `connect EPERM localhost:5432` | Also has teardown error below from same fixture. |
| `evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_get_sample_count_with_track_record` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | `_resolve_n()` sets `past = now - 1h`, then `ledger.pre_register()` rejects it | Calibration regression test must use explicit historical-registration path or future registration plus valid resolution strategy. |
| `evals/regression/test_audit_findings.py::TestHigh1SampleCount::test_execute_action_does_not_crash_for_agent_with_history` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | same `_resolve_n()` helper uses backdated registration | Touches calibration/trust/escalation path. |
| `evals/regression/test_audit_findings.py::TestHigh3DowngradePropagation::test_downgrade_propagates_to_consumers` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | same `_resolve_n()` helper uses backdated registration | Touches calibration trust downgrade propagation. |
| `evals/regression/test_v2_regression.py::TestInvariant1_ImmutableLedger::test_resolution_write_once` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | test sets `resolution_date=datetime.now(...) - timedelta(hours=1)` before `pre_register()` | Touches calibration ledger immutability/write-once behavior. |
| `evals/regression/test_v2_regression.py::TestInvariant10_GroundTruthExternal::test_internal_resolution_source_rejected` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | test attempts to reach resolution-source rejection but uses a backdated registration first | Touches calibration source-externality behavior. |
| `evals/regression/test_v2_regression.py::TestSeededFalseBeliefRegression::test_seeded_false_belief_cannot_reach_reality_validated` | `ValueError: resolution_date must be in the future for pre-registration` | REGRESSION | test registers three predictions with `past = now - 1h` | Touches calibration/firewall/trust acceptance path. |
| `learning/tests/test_learning_loop.py::TestScenarioAgent::test_generates_hypotheses_for_focus_areas` | `KeyError: 'count'` | STALE | test expects `result["count"]`; current `ScenarioAgent.generate_hypotheses()` returned a different shape after escalation/degradation path | Candidate update: assert current envelope or blocked/escalated shape explicitly. |
| `tests/test_db_client_runtime_config.py::test_backend_db_client_has_bounded_pool_and_retry_contract` | expected literal `max: 20` absent from `backend/src/db/client.ts` | STALE | source-text test asserts implementation strings, not behavior | Candidate update: parse/export config or assert runtime Pool options through a stable contract. |
| `tests/test_specialist_agent.py::TestResearcherAgent::test_web_search_action` | expected `search_completed`, got `failed` | STALE | specialist unit test expects old happy-path search behavior without configured/available service | Candidate update: inject a fake search adapter or assert failure shape. |
| `tests/test_specialist_agent.py::TestResearcherAgent::test_fetch_page_action` | expected `fetch_completed`, got `failed` | STALE | specialist unit test expects old fetch behavior in environment without network/service fixture | Candidate update: inject fixture adapter. |
| `tests/test_specialist_agent.py::TestResearcherAgent::test_generate_claim_action` | expected `claim_generated`, got `failed` | STALE | captured output shows DB pool initialization failed and claim retries | Either mark live DB requirement or inject fake DB. |
| `tests/test_specialist_agent.py::TestFetcherAgent::test_fetch_allowed` | expected `fetch_completed`, got `failed` | STALE | same specialist fetch path returns failure in clean environment | Candidate update: inject fixture adapter. |
| `tests/test_specialist_isolation_verification.py::test_specialist_isolation_execution` | `UnboundLocalError` after DB connection failure | STALE | root cause is `psycopg2.OperationalError`; secondary bug in `agents/db/connection.py:82` rolls back unbound `conn` | Should be skipped without DB; connection helper also needs defensive rollback later. |
| `agents/tests/integration/test_agent_dispatch_e2e.py::test_full_dispatch_path_touches_real_postgres_ledger_audit_and_kafka` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | output shows `connect EPERM localhost:5432`; test name requires real Postgres/Kafka | Should be marked skip unless services are configured/reachable. |
| `agents/tests/integration/test_tool_execution_real.py::test_denial_via_base_agent_writes_real_audit_entry` | teardown error: localhost Postgres `OperationalError` | LIVE-SERVICE | `_setup` cleanup opens `_conn()` after test; output shows `connect EPERM localhost:5432` | Same live DB requirement as failures in this module. |
| `reserve/tests/test_agent_reserve_integration.py::test_agent_earns_reserve_credential_from_real_predictions` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | output shows socket `/tmp/.s.PGSQL.5432` `Operation not permitted` | Should skip unless `AGENTCO_TEST_DATABASE_URL` points to reachable isolated DB. |
| `reserve/tests/test_oracle_layer.py::test_oracle_resolves_prediction_and_records_standing` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | module fixture calls `psycopg2.connect(DSN)`; output shows `/tmp/.s.PGSQL.5432` | Should skip when isolation DB cannot be created/reached. |
| `reserve/tests/test_oracle_layer.py::test_higher_authority_oracle_contradicts_lower` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_oracle_layer.py::test_mechanical_ground_truth_contradicts_oracle_and_docks_standing` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_oracle_layer.py::test_unqualified_agent_cannot_act_as_oracle` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_oracle_layer.py::test_write_trace` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_proof_of_calibration.py::test_deterministic_scoring_recomputes_identically` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | output shows `/tmp/.s.PGSQL.5432` `Operation not permitted` | Should skip when DB unavailable. |
| `reserve/tests/test_proof_of_calibration.py::test_two_agents_with_different_track_records_produce_different_credentials` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_proof_of_calibration.py::test_fresh_agent_has_neutral_low_standing` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_proof_of_calibration.py::test_write_trace` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_staking_and_decisions.py::test_weighted_decision_follows_credential_weight` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | output shows `/tmp/.s.PGSQL.5432` `Operation not permitted` | Should skip when DB unavailable. |
| `reserve/tests/test_staking_and_decisions.py::test_sybil_identities_have_zero_weight` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_staking_and_decisions.py::test_stake_is_write_once` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_staking_and_decisions.py::test_collusion_resistance_property_audit_values` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `reserve/tests/test_staking_and_decisions.py::test_write_trace` | setup error: Postgres socket `OperationalError` | LIVE-SERVICE | same module fixture | Should skip when DB unavailable. |
| `runtime/tests/test_spend_guardrail_ledger.py::test_spend_guardrail_reserves_and_settles_real_ledger` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | `_apply_migrations()` calls `psycopg2.connect(_dsn())`; output shows `connect EPERM localhost:5432` | Should skip on unreachable DB, not only missing DSN. |
| `runtime/tests/test_spend_guardrail_ledger.py::test_spend_guardrail_releases_pending_reservation_on_failed_call` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | same autouse fixture | Should skip on unreachable DB. |
| `runtime/tests/test_spend_guardrail_ledger.py::test_spend_guardrail_blocks_when_real_ledger_budget_is_missing` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | same autouse fixture | Should skip on unreachable DB. |
| `runtime/tests/test_spend_guardrail_ledger.py::test_structured_output_releases_ledger_hold_when_provider_call_fails` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | same autouse fixture | Should skip on unreachable DB. |
| `tests/test_civilization_free_run_positive_path.py::test_execute_goals_positive_path` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | fixture applies real DB migrations; output shows `connect EPERM localhost:5432` | Should skip on unreachable DB. |
| `tests/test_civilization_free_run_positive_path.py::test_run_free_run_positive_path` | setup error: localhost Postgres `OperationalError` | LIVE-SERVICE | same fixture | Should skip on unreachable DB. |

