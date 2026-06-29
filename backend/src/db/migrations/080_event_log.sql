-- Migration 080: Canonical L3 event log.
--
-- event_history remains the legacy bus/history table. event_log is the
-- civilization-level ordered, hash-chained event spine required by the
-- architecture plan.

CREATE TABLE IF NOT EXISTS event_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  institution_id UUID,
  object_type TEXT,
  object_id UUID,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  correlation_id UUID NOT NULL,
  causation_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  signature TEXT,
  prev_hash TEXT NOT NULL,
  event_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_log_type ON event_log(event_type);
CREATE INDEX IF NOT EXISTS idx_event_log_actor ON event_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_event_log_correlation ON event_log(correlation_id);
CREATE INDEX IF NOT EXISTS idx_event_log_occurred ON event_log(occurred_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_event_log_object ON event_log(object_type, object_id);

REVOKE DELETE ON event_log FROM PUBLIC;
REVOKE UPDATE ON event_log FROM PUBLIC;
