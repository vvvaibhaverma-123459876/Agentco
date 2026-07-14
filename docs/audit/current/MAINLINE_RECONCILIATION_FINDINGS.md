# Mainline Reconciliation Findings

## CVR-001 — Duplicate 129 Migration Prefix Without Identity Hashing

- Severity: S2
- Subject: raw Version B, `651794a41513db1e40930f08c253ef261af7c1e7`
- Evidence: `backend/src/db/migrations/129_civilization_kernel.sql` and `backend/src/db/migrations/129_longitudinal_mission_evidence.sql` both exist.
- Root cause: PR #25 and PR #26 were developed independently and allocated the same numeric migration prefix.
- Impact: Prefix-only migration reasoning is ambiguous, and the pre-existing migration runner did not detect changed contents under an already-applied filename.
- Remediation: Version C adds content-hash and sequence tracking to `schema_migrations`, plus `scripts/verify_migration_identity.py` and `MIGRATION_IDENTITY_LEDGER`.
- Status: Resolved in Version C.

## CVR-002 — Generated Artifact Drift Risk After Parallel Merges

- Severity: S3
- Subject: generated audit reports and score snapshots.
- Evidence: both lineages modified generated forensic, route, runtime, and score artifacts.
- Impact: Stale generated reports could overstate the current tree if not checked.
- Remediation: Existing generated-report freshness checks remain mandatory through `make release-gate`.
- Status: Monitored.

## Version C Freeze Rule

No benchmark cases, hidden expectations, or evaluator semantics were changed during reconciliation.
