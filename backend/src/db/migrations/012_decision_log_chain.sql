-- Add hash-chain columns to decision_log so the AuditLogService can persist and
-- verify the full chain. chain_hash is the SHA-256 of (prev_hash || row content);
-- prev_hash is the chain_hash of the immediately preceding row (or all-zeros for
-- the first row). Both are immutable after insert — the UPDATE revocation on
-- decision_log already enforces this at the DB layer.
ALTER TABLE decision_log
  ADD COLUMN IF NOT EXISTS chain_hash TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS prev_hash  TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_decision_log_chain ON decision_log(timestamp ASC, log_id ASC);
