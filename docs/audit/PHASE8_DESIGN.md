# Phase 8 Design Notes

## Task 1 — Tamper-Evident Serialization Versioning

### Current Problem

Phase 5 made TS and Python writers converge on sorted-key compact JSON for
`decision_log` chain hashes, but the row does not record which serialization
contract produced `chain_hash`. `verifyChainIntegrity()` therefore accepts a
set of candidate hashes per row:

- `v2.sorted-json`
- `v1.ts-insertion-json`
- `v1.python-insertion-json`
- `v1.python-sorted-json-spaced`

That candidate acceptance is necessary for historical rows, but it is unsafe as
a forward protocol: a buggy writer can keep emitting a legacy-valid hash and the
verifier will accept it forever.

### Chosen Semantics

Add migration `125_decision_log_protocol_version.sql`:

- Add nullable `decision_log.serialization_version TEXT`.
- Record the migration-time cutoff in a table
  `decision_log_protocol_cutoff` as `(id, cutoff_timestamp, cutoff_log_id)`,
  using the current max chain row ordered by `(timestamp, log_id)`.
- Historical rows at or before the cutoff may omit `serialization_version` and
  continue to use candidate verification.
- Any row after the cutoff with `serialization_version IS NULL` is invalid.
- New rows use `serialization_version = 'v3.sorted-json-versioned'`.

For `v3.sorted-json-versioned`, `serialization_version` is included inside the
canonical hashed payload. A row cannot claim a different version than the one it
was hashed under without breaking `chain_hash`.

Verification becomes:

- If `serialization_version` is present: verify only the named version. No
  candidate fallback.
- If `serialization_version` is absent and the row is historical according to
  the cutoff: verify with the existing legacy candidate set.
- If `serialization_version` is absent and the row is post-cutoff: fail.

Both writers stamp `v3.sorted-json-versioned` and include that field in hashed
material. The TS writer inserts it directly; the Python durable writer uses the
same string and the same sorted compact JSON function.

### Tests

Extend the live cross-writer chain test:

- Assert TS -> Python -> TS rows all have `serialization_version`.
- Assert a valid new row verifies under exactly one version.
- Negative: a new row with a version field but a hash computed under another
  canonicalization fails verification.
- Negative: a post-cutoff row missing `serialization_version` fails.
- Negative: tampering with `serialization_version` on a valid row fails.

The negative tests use the migration/admin test connection to bypass
append-only update triggers only for tamper simulation; runtime writers still
use the app connection.

### Rejected Alternatives

- **Keep candidate fallback forever.** Rejected because it leaves version choice
  advisory and allows future legacy-valid rows to pass.
- **Backfill historical rows with guessed versions.** Rejected because existing
  rows can be valid under multiple historical candidates; guessing would create
  false precision.
- **Use only a code constant cutoff.** Rejected because the cutoff must match
  the deployed database state at migration time. Recording it in the migration
  table makes the verifier use the same seam the database observed.
