-- Migration 145 (AUD-013): DB-enforced idempotency for judiciary case intake.
--
-- judiciary_cases.source_dispute_id (the upstream dispute/escalation this case was opened for)
-- had no uniqueness constraint. openCase() did a bare INSERT with no idempotency check, and its
-- one caller with a check-then-act guard (routeEscalationsToJudiciary in civilization-os.service.ts)
-- splits that check and the INSERT across two separate database connections/transactions -- not
-- atomic, so it is not a real guarantee against a genuine race, only against the one specific
-- crash-recovery sequencing it happened to be written for. A retried HTTP POST, a concurrent
-- orchestration tick, or a direct-SQL writer could all still open two judiciary cases for the same
-- underlying dispute.
--
-- A partial unique index (source_dispute_id IS NOT NULL) is the DB-level backstop: it allows
-- multiple cases with no source dispute (opened directly by a human complainant with nothing
-- upstream to key on) while enforcing true uniqueness whenever a source_dispute_id is given,
-- regardless of which connection, transaction, or writer performs the INSERT.

CREATE UNIQUE INDEX IF NOT EXISTS uq_judiciary_cases_source_dispute_id
  ON judiciary_cases (source_dispute_id)
  WHERE source_dispute_id IS NOT NULL;
