-- Migration 096: Shared idempotency store
--
-- Provides a canonical request idempotency ledger for runtime services that do
-- not already have a domain-specific idempotency key.

CREATE TABLE IF NOT EXISTS idempotency_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  status TEXT NOT NULL CHECK (status IN ('in_progress', 'completed', 'failed')),
  response_json JSONB,
  error_message TEXT,
  started_event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  completed_event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (scope, idempotency_key)
);

CREATE INDEX IF NOT EXISTS idx_idempotency_records_scope_status
  ON idempotency_records(scope, status);

CREATE INDEX IF NOT EXISTS idx_idempotency_records_actor
  ON idempotency_records(actor_id);
