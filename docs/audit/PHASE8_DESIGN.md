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

## Task 2 — Idempotent Audit Write/ACK

### Current Problem

`DurableAuditWriter.write()` appends a row and returns only after the DB commit
completes. If the commit succeeds but the acknowledgement path fails before the
caller receives `log_id`, the caller raises `AuditUnavailableError`. A retry is
currently a new append because no stable event identity is persisted in
`decision_log`.

Both writers also assign `prev_hash` in application code by selecting the latest
row before insert. Without serialization around that read/insert pair, two
concurrent writers can pick the same head. The Task 2 idempotency fix prevents
duplicate rows for the same logical event, but the chain-head race is still part
of the protocol story and should be closed at the same boundary.

### Chosen Semantics

Add migration `126_decision_log_attempt_id.sql`:

- Add nullable `decision_log.attempt_id UUID`.
- Add a unique index for non-null `attempt_id`.
- Historical rows may omit `attempt_id`.

New rows use `serialization_version = 'v4.sorted-json-versioned-attempt'`.
The v4 canonical payload includes `serialization_version` and `attempt_id`.
The verifier supports both explicit versions:

- `v3.sorted-json-versioned`: requires and hashes `serialization_version`.
- `v4.sorted-json-versioned-attempt`: requires and hashes both
  `serialization_version` and `attempt_id`.

The Python durable writer generates one UUID attempt id before the first write
attempt for a logical audit event and reuses it across bounded retries. The TS
writer also stamps an attempt id so both writers remain symmetric.

Write protocol for both writers:

1. Begin transaction.
2. Acquire a transaction-scoped advisory lock for the decision-log hash chain.
3. Read the current chain head and compute the v4 hash once for this attempt.
4. `INSERT ... ON CONFLICT (attempt_id) DO NOTHING`.
5. `SELECT` the row by `attempt_id`; either the insert or a previous committed
   attempt is success.
6. Commit and return an acknowledgement.

For a lost acknowledgement after commit, the retry uses the same `attempt_id`;
the conflict path returns the existing row and does not append a second link.
For a genuine write failure before commit, all retries fail and the caller sees
`AuditUnavailableError`; high/critical action execution remains blocked until an
acknowledgement is returned.

### Concurrency Story

`prev_hash` remains application-assigned, but the advisory transaction lock
serializes the chain-head read and insert for all current TS and Python writers.
Concurrent retries of the same logical event cannot compute and commit two
different rows because `attempt_id` is unique. Concurrent different events wait
on the same lock, observe the latest committed head, and append in transaction
order.

The lock is cooperative: it protects writers that use the protocol. A raw SQL
writer that bypasses `AuditLogService`/`DurableAuditWriter` can still create a
branch. That is a deliberate boundary for this phase; route/tool code should use
the protocol writers, and direct table writes remain a privileged/debug path.

### Tests

- Live Python test: simulate a lost acknowledgement after the first committed
  insert; retry with the same attempt id; assert exactly one `decision_log` row
  and the action receives an acknowledgement.
- Live Python test: simulate repeated write failure before insert; assert
  `AuditUnavailableError` and zero rows for the attempt id.
- Live cross-writer test: assert new TS/Python rows use v4, carry
  `attempt_id`, and verify under exactly one candidate.
- TS unit/integration coverage: duplicate `attempt_id` append returns the
  original row rather than appending.

### Rejected Alternatives

- **Use `log_id` as the idempotency key.** Rejected because callers do not know
  it before the first write attempt and cannot reuse it after a lost ack unless
  it is promoted into a separate attempt identity.
- **Make Python idempotent but leave TS unchanged.** Rejected because both
  writers append to the same chain; asymmetric semantics would preserve an
  avoidable protocol split.
- **Rely only on `ON CONFLICT` without a chain lock.** Rejected because it fixes
  duplicate retries for the same event but leaves concurrent different events
  able to select the same previous hash.
