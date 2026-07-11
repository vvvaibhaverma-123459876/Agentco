-- Migration 128: Durable outbox for legacy EventBusService publishes.
--
-- event_outbox is tied to the canonical event_log spine. EventBusService still
-- writes legacy event_history rows for service-to-service envelopes, so this
-- table preserves the same outbox semantics for that path without weakening
-- event_history immutability.

CREATE TABLE IF NOT EXISTS event_bus_outbox (
  event_id UUID PRIMARY KEY REFERENCES event_history(event_id) ON DELETE RESTRICT,
  topic TEXT NOT NULL,
  signed_envelope JSONB NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_event_bus_outbox_pending
  ON event_bus_outbox(status, next_attempt_at, created_at);

CREATE TABLE IF NOT EXISTS event_bus_dead_letters (
  event_id UUID PRIMARY KEY REFERENCES event_history(event_id) ON DELETE RESTRICT,
  topic TEXT NOT NULL,
  signed_envelope JSONB NOT NULL,
  attempts INTEGER NOT NULL CHECK (attempts > 0),
  error TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

REVOKE DELETE ON event_bus_outbox FROM PUBLIC;
REVOKE DELETE ON event_bus_dead_letters FROM PUBLIC;
