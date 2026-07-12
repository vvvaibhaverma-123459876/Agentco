# Remediation 02A — Clean-Room Evidence

## Original Findings

- `make verify-clean-room` accepted caller-supplied database state and therefore could not prove version-zero migration from an empty database.
- Python skips were reported only as an aggregate count.
- Tracked structural reports were described with wording that implied exact-HEAD runtime evidence.
- The gate-integrity scanner covered only a narrow subset of active verification surfaces.
- Clean-room runs did not produce a complete machine-readable command execution ledger.

## Root Causes

- Clean-room verification was implemented as a Makefile recipe over ambient developer services.
- Skip governance was not separated from normal pytest execution.
- Structural score validation mixed stale-report freshness wording with runtime proof language.
- Gate-integrity exceptions were hardcoded in the scanner instead of governed data.
- Runtime evidence was not modeled as an ignored artifact.

## Controls Added

- `make audit-clean-room` now invokes `scripts/audit_clean_room.py`, which owns a unique PostgreSQL container, volume, database, command ledger, migration reports, pytest reports, and cleanup.
- `scripts/verify_migration_integrity.py` validates migration ordering, static effect statements, empty database state, applied migration records, expected schema objects, and second-run idempotency through schema fingerprints.
- `scripts/verify_pytest_skips.py` and `pytest_skip_report_plugin.py` capture exact pytest outcomes and enforce `docs/audit/current/TEST_SKIP_ALLOWLIST.json`.
- `scripts/verify_execution_ledger.py` rejects runtime evidence whose commit or command results do not match the checked-out repository.
- `scripts/verify_gate_integrity.py` scans active gate surfaces recursively and uses `docs/audit/current/GATE_INTEGRITY_EXCEPTIONS.json` for expiring, matched exceptions.
- `.github/workflows/clean-room-audit.yml` runs `make audit-clean-room` and uploads `artifacts/audit/` even when the audit fails.

## Threat Model

The controls defend against false clean-room success caused by contaminated databases, zero-test pytest runs, ungoverned skips, stale structural reports, masked command failures, stale gate exceptions, missing command ledgers, and cleanup paths that hide resource leaks.

## Failure Modes Covered

- Non-empty clean-room database before migration.
- Missing, stale, expired, or unapproved skip allowlist entries.
- Unexpected xpass, deselection, or zero collected tests.
- Migration files without deterministic prefixes or schema/data effects.
- Migration records missing after application.
- Second migration run changing schema.
- Protected scripts or workflows using `|| true`, `continue-on-error`, `--forceExit`, `passWithNoTests`, explicit `check=False`, or production-ready success language without a governed exception.
- Runtime evidence recorded for a commit other than `HEAD`.
- Command failure recorded as success.
- Cleanup failure after a failed audit.

## Files Changed

- `Makefile`
- `.gitignore`
- `.github/workflows/clean-room-audit.yml`
- `backend/src/cli/score-validation.ts`
- `docs/CURRENT_RUNTIME_CANONICAL.md`
- `docs/audit/current/GATE_INTEGRITY_EXCEPTIONS.json`
- `docs/audit/current/TEST_SKIP_ALLOWLIST.json`
- `pytest_skip_report_plugin.py`
- `scripts/audit_clean_room.py`
- `scripts/verify_execution_ledger.py`
- `scripts/verify_gate_integrity.py`
- `scripts/verify_migration_integrity.py`
- `scripts/verify_pytest_skips.py`
- `tests/test_clean_room_evidence_controls.py`
- `evals/regression/test_gate17_ci_master.py`

## Commands Executed

Final command evidence is recorded in the latest `artifacts/audit/<run-id>/EXECUTION_LEDGER.json` after `make audit-clean-room` completes. The runtime ledger records the exact commit SHA, branch, command list, exit codes, migration summary, skip summary, and cleanup result.

## Skip Counts and Classification

The governed allowlist is stored at `docs/audit/current/TEST_SKIP_ALLOWLIST.json`. Runtime skip counts are emitted per run to `artifacts/audit/<run-id>/test-results/pytest-summary.json`.

## Migration Results

Runtime migration results are emitted per run to `artifacts/audit/<run-id>/migration-results/`.

## Known Limitations

- This is local clean-room evidence, not hosted production or staging proof.
- External model providers, live web providers, Kubernetes deployment, long-horizon learning, and production alert delivery remain explicitly unverified unless separate live/staging commands are run with real infrastructure.
- Legacy non-canonical Make helpers still exist. Their bypass-like patterns are governed by expiring exceptions and are not accepted as release or clean-room proof.

## Rollback Procedure

Revert this remediation commit to restore the previous `verify-clean-room` behavior. That rollback would also remove the isolated audit command and should be treated as a loss of clean-room evidence guarantees.

## Final Commit

The immutable branch-tip SHA is recorded by `git rev-parse HEAD` and in the runtime execution ledger for each clean-room run. This report does not embed the hash of the commit that contains it because doing so would change that hash; the final response records the pushed branch tip.
