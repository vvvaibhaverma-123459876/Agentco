# AUD-013 — Judiciary case idempotency

## Finding

`judiciary_cases.source_dispute_id` (the upstream dispute/escalation a case was opened for) had
no uniqueness constraint. `JudiciaryCaseService.openCase()` performed a bare `INSERT` with no
idempotency check of any kind.

Its one production caller with a guard, `routeEscalationsToJudiciary()` in
`civilization-os.service.ts`, does a `SELECT ... WHERE source_dispute_id = $1` before calling
`openCase()` — but that check runs on the orchestration tick's own transaction/connection, while
`openCase()` opens and commits an entirely separate connection and transaction. A check-then-act
guard split across two independent transactions is not atomic: it happens to be correct for the
one specific crash-recovery scenario it was written for (a tick that dies after `openCase()`
commits but before the escalation is marked `routed` will, on retry, see the already-committed
case and skip re-opening it), but it provides no protection against a genuine concurrent race — a
retried HTTP `POST /api/civilization/judiciary/cases`, two orchestration ticks overlapping, or a
direct-SQL writer could all still open two judiciary cases for the same underlying dispute.

## Fix

**Migration 145** adds a partial unique index:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_judiciary_cases_source_dispute_id
  ON judiciary_cases (source_dispute_id)
  WHERE source_dispute_id IS NOT NULL;
```

Partial, not a plain `UNIQUE` column constraint, because `source_dispute_id` is legitimately
`NULL` for cases opened directly by a human complainant with nothing upstream to key on — those
must remain free to coexist.

**`JudiciaryCaseService.openCase()`** catches the resulting unique-violation (Postgres error code
`23505` on constraint `uq_judiciary_cases_source_dispute_id`) and resolves it to the case that
already exists for that `source_dispute_id`, returning it instead of surfacing a raw constraint
error to the caller. This makes `openCase()` itself genuinely idempotent for any caller —
independent of which connection, transaction, or code path performs the call — rather than relying
on callers to each reimplement their own (necessarily non-atomic, since the INSERT itself is not
under their control) check-then-act guard.

`routeEscalationsToJudiciary()`'s existing pre-check is left in place as a fast-path optimization
(avoids an unnecessary write attempt and the resulting rollback in the common case), with its
comment corrected to describe the DB constraint — not the pre-check — as the actual guarantee.

## Verification

`backend/tests/aud013-judiciary-idempotency.test.ts`:
- Direct-SQL bypass: a second `INSERT` reusing a `source_dispute_id` is rejected by Postgres
  itself, independent of the service layer.
- Sequential `openCase()` calls with the same `source_dispute_id` return the same case; only one
  row exists.
- **Concurrent, racing** `openCase()` calls (fired via `Promise.all`, not sequentially) with the
  same `source_dispute_id` resolve to the same case — this is the actual race the DB constraint
  exists to close, and the one the old check-then-act guard could not.
- Cases with no `source_dispute_id` are unaffected (multiple may coexist).
- Cases with distinct `source_dispute_id` values are unaffected (no over-broad blocking).

## Explicitly out of scope

This closes the *duplicate-case* risk only. It does not address the broader judiciary-enforcement
gaps found by the independent subsystem audit dated 2026-07-20 (`citizen_sanction` orders that
never flip a citizen's execution-gating status; `trust_adjustment`/`capability_revocation` orders
that are accepted and never dispatched; the claim/evidence-contradiction dispute path bypassing
this case machinery entirely in favor of a separate, no-hearing auto-ruling service). Those are
independent findings, not remediated here.
