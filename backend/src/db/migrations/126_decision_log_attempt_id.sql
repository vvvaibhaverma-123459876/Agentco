-- Phase 8 Task 2: idempotent audit write/ACK.
--
-- New protocol rows carry a stable attempt_id so retries after a lost ACK can
-- acknowledge the already-committed row instead of appending a duplicate.
ALTER TABLE decision_log
  ADD COLUMN IF NOT EXISTS attempt_id UUID;

CREATE UNIQUE INDEX IF NOT EXISTS idx_decision_log_attempt_id_unique
  ON decision_log(attempt_id)
  WHERE attempt_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_decision_log_attempt_id
  ON decision_log(attempt_id);
