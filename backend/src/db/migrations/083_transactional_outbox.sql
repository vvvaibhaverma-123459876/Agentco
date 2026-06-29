-- Migration 083: L3 transactional outbox.
--
-- Canonical events written to event_log are atomically enqueued here in the
-- same database transaction. A relay can publish pending rows to Kafka or any
-- other real event sink after commit without risking state/event split-brain.

CREATE TABLE IF NOT EXISTS event_outbox (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_log_id UUID NOT NULL UNIQUE REFERENCES event_log(id) ON DELETE RESTRICT,
  topic TEXT NOT NULL,
  envelope JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'publishing', 'published', 'failed', 'dead_lettered')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  locked_by TEXT,
  locked_at TIMESTAMPTZ,
  published_at TIMESTAMPTZ,
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_outbox_pending
  ON event_outbox(status, next_attempt_at, created_at);
CREATE INDEX IF NOT EXISTS idx_event_outbox_event
  ON event_outbox(event_log_id);

CREATE TABLE IF NOT EXISTS event_dead_letters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outbox_id UUID NOT NULL UNIQUE REFERENCES event_outbox(id) ON DELETE RESTRICT,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  topic TEXT NOT NULL,
  envelope JSONB NOT NULL,
  attempts INTEGER NOT NULL CHECK (attempts > 0),
  error TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_dead_letters_event
  ON event_dead_letters(event_log_id);

REVOKE DELETE ON event_outbox FROM PUBLIC;
REVOKE DELETE ON event_dead_letters FROM PUBLIC;
