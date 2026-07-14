# Cross-Version Findings

## CVF-001 — Version B Migration Identity Ambiguity

- Severity: S2
- Subject: Version B, `651794a41513db1e40930f08c253ef261af7c1e7`
- Component: database migrations
- Evidence: Version B contains both `129_civilization_kernel.sql` and `129_longitudinal_mission_evidence.sql`, while the migration runner records only `filename` and `applied_at`.
- Root cause: PR #25 and PR #26 allocated the same numeric migration prefix independently.
- Impact: Lexicographic execution remains deterministic, but audit identity and already-applied content mismatch detection were insufficient.
- Remediation: Version C adds content-hash tracking and `scripts/verify_migration_identity.py`.
- Status: resolved in Version C.
