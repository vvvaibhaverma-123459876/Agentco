# Remediation 02B: Clean-Room Closure

## Scope

Batch 02B closes the remaining clean-room audit integrity gaps from Batch 02A. It does not claim hosted production readiness, external provider verification, Kubernetes deployment verification, long-horizon learning proof, or a full repository line audit.

## Remaining Defects After Batch 02A

1. Environment-aware skip validation parsed `required_environment` but did not fail when a test skipped despite the required service being available.
2. PostgreSQL-backed tests could remain allowlisted as clean-room skips even though `make audit-clean-room` provisions a disposable PostgreSQL database.
3. Mixed PostgreSQL plus Kafka tests could hide database setup defects behind a generic live-service skip reason.
4. `make audit-clean-room` invoked a nested `make release-gate`, which duplicated the governed Python suite and obscured per-command evidence.
5. The runtime ledger recorded top-level audit actions, but did not embed top-level pytest and skip summaries until this batch.

## Root Cause

The clean-room audit originally treated skip governance as a static allowlist check. It did not evaluate whether each allowlisted dependency was actually available during the current run. The audit also delegated source verification to a nested make target, so some command outcomes were visible only in top-level stdout rather than in structured, command-by-command evidence.

## Controls Added

- `scripts/verify_pytest_skips.py` now supports structured environment requirements with `present`, `absent`, `equals`, `not_equals`, `postgres_reachable`, and `kafka_reachable`.
- A skip now fails with `SKIP_DESPITE_AVAILABLE_ENVIRONMENT` when all required dependencies for that allowlist entry are available.
- Database-backed skips classified as `external_network` fail with `DB_SKIP_CLASSIFIED_EXTERNAL_NETWORK`.
- Skip reasons that claim a database variable is missing while it is present fail with `DB_VAR_PRESENT_BUT_REASON_CLAIMS_MISSING`.
- Mixed-service skips are accepted only for the actually unavailable boundary.
- `scripts/audit_clean_room.py` executes each release-gate component once and records each material command with `command_id`, redacted argv, cwd, environment variable names, timestamps, exit code, artifact paths, run ID, and commit SHA.
- Cleanup steps are recorded as command evidence and verified by checking that the named Docker container and volume no longer exist.
- `scripts/verify_execution_ledger.py` now rejects missing command records, wrong run IDs, wrong commits, failed required commands, missing artifacts, unredacted secrets, missing test summaries, and missing skip summaries.

## Previous DB-Backed Skips Now Exercised

These clean-room skips from Batch 02A are now required to run when the disposable PostgreSQL database is available:

- `reserve/tests/test_independent_recomputation.py::test_stored_credential_score_matches_independent_recomputation`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_role_created`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_can_connect`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_can_select_from_allowed_tables`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_cannot_insert`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_cannot_update`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_cannot_delete`
- `tests/integration/test_resolution_service_role_migration.py::test_resolution_service_cannot_drop_table`
- `tests/test_specialist_agent.py::TestEvidenceSummarizerAgent::test_extract_evidence`

Final local clean-room evidence at `artifacts/audit/20260713T061027Z-b7affa29/` shows `720 collected`, `715 passed`, `5 skipped`, `0 failed`, `0 xfailed`, `0 xpassed`. Remaining skips are only:

- `live_provider=3`: live LLM memory lifecycle tests requiring `RUN_REAL_LLM_TESTS=1` and working credentials.
- `other=2`: slow load tests requiring `SKIP_LOAD_TEST=0`.

No PostgreSQL-backed clean-room skips remain in that run.

## Release-Gate Deduplication Design

`make release-gate` remains the canonical standalone local source verification command.

`make audit-clean-room` is the strongest local audit command. It owns disposable PostgreSQL infrastructure, runs migrations from version zero, verifies idempotency, then executes each release-gate component exactly once through the clean-room evidence wrapper rather than nesting `make release-gate`.

The final ledger command IDs are:

`docker-version`, `docker-postgres-start`, `create-database`, `migration-static-integrity`, `database-empty-before-migration`, `backend-install`, `migrate-from-zero`, `database-after-migration`, `migrate-idempotency-second-run`, `release-gate-integrity`, `release-make-targets`, `release-status-check`, `release-agent-protocol-matrix-check`, `release-evaluation-calibration-report-check`, `release-controlled-learning-report-check`, `release-self-improvement-report-check`, `release-score-validation`, `pytest-governed`, `backend-build`, `backend-jest`, `backend-route-auth-contract`, `backend-audit-chain-cross-writer`, `frontend-install`, `frontend-typecheck`, `frontend-build`, `cleanup-drop-database`, `cleanup-remove-container`, `cleanup-remove-volume`, `cleanup-verify-container-removed`, `cleanup-verify-volume-removed`.

## Command-Ledger Completeness

Local final evidence path:

- `artifacts/audit/20260713T061027Z-b7affa29/EXECUTION_LEDGER.json`
- `artifacts/audit/20260713T061027Z-b7affa29/AUDIT_SUMMARY.md`
- `artifacts/audit/20260713T061027Z-b7affa29/commands/`
- `artifacts/audit/20260713T061027Z-b7affa29/test-results/`
- `artifacts/audit/20260713T061027Z-b7affa29/migration-results/`

Ledger validation:

```text
python3.13 scripts/verify_execution_ledger.py artifacts/audit/20260713T061027Z-b7affa29/EXECUTION_LEDGER.json
{"errors": [], "success": true}
```

## Secret-Redaction Controls

The command ledger stores environment variable names, not values. Command argv is redacted for PostgreSQL URL passwords and secret-like assignments containing `PASSWORD`, `TOKEN`, `SECRET`, `API_KEY`, or `AUTHORIZATION`.

Local redaction check on the final ledger:

```text
db_secret_match False
secret_assignment_match False
```

## Cleanup Verification

Final local cleanup result:

```json
{
  "success": true,
  "steps": {
    "cleanup-drop-database": {"exit_code": 0},
    "cleanup-remove-container": {"exit_code": 0, "success": true},
    "cleanup-remove-volume": {"exit_code": 0, "success": true},
    "cleanup-verify-container-removed": {"exit_code": 1, "success": true},
    "cleanup-verify-volume-removed": {"exit_code": 1, "success": true}
  }
}
```

The non-zero inspect exit codes are expected and mean the named container and volume no longer exist.

## Negative-Test Coverage

`tests/test_clean_room_evidence_controls.py` exercises the actual validators and orchestration helpers for:

- unapproved skip rejection
- expired and stale skip entries
- zero-test and xpass rejection
- `SKIP_DESPITE_AVAILABLE_ENVIRONMENT`
- database skip classified as external network
- wrong missing-service skip reason
- malformed environment condition
- migration static integrity failures
- wrong ledger commit
- wrong ledger run ID
- unredacted secret detection
- missing command records
- missing test and skip summaries
- command failure recording
- cleanup failure detection

Focused result:

```text
python3.13 -m pytest tests/test_clean_room_evidence_controls.py -q
16 passed
```

## Commands Executed

```text
python3.13 -m pytest tests/test_clean_room_evidence_controls.py -q
python3.13 scripts/verify_gate_integrity.py --check
python3.13 scripts/verify_make_targets.py --check
cd backend && npm run agentco:score-validation
make release-gate
make audit-clean-room
python3.13 scripts/verify_execution_ledger.py artifacts/audit/20260713T061027Z-b7affa29/EXECUTION_LEDGER.json
```

## GitHub Actions Evidence

GitHub Actions evidence is required before this batch is complete. The final run ID, artifact ID, artifact name, artifact SHA-256, and commit equality check are recorded in the final handoff response after the workflow runs against the branch head.

## Remaining External Limitations

- Live LLM provider tests remain governed skips unless `RUN_REAL_LLM_TESTS=1` and provider credentials are available.
- Slow load tests remain governed skips unless `SKIP_LOAD_TEST=0`.
- This batch does not verify hosted Kubernetes deployment, production secrets, live provider behavior, or long-horizon mission claims.

## Rollback Procedure

Revert the Batch 02B commits on `audit/remediation-02b-clean-room-closure`. The rollback returns the repository to Batch 02A behavior, where clean-room evidence is less strict and PostgreSQL-backed skips may be accepted incorrectly. After rollback, rerun:

```text
python3.13 scripts/verify_gate_integrity.py --check
python3.13 scripts/verify_make_targets.py --check
make release-gate
make audit-clean-room
```

## Commit Reference

Implementation commit before this tracked report was added: `11178e2a4c39f138b50feec42b5d0c1e50812508`.

The exact final branch tip cannot be embedded in the same commit that creates this file without becoming self-referential. Exact-HEAD runtime evidence is recorded in the clean-room execution ledger and the final response.
