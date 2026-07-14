-- Migration 140: governed capability runtime foundation.
-- Stores versioned capability attempts, provider calls, tool calls, memory
-- events, authorization decisions, budget ledger entries and recovery events.

CREATE TABLE IF NOT EXISTS capability_attempts (
  attempt_id TEXT PRIMARY KEY,
  request_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN (
    'completed',
    'failed',
    'timed_out',
    'cancelled',
    'denied',
    'budget_exceeded',
    'unsupported',
    'partially_completed'
  )),
  task_type TEXT NOT NULL,
  actor_id TEXT,
  tenant TEXT NOT NULL,
  request_json JSONB NOT NULL,
  response_json JSONB NOT NULL,
  request_hash TEXT,
  response_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_capability_attempts_request_id
  ON capability_attempts (request_id);

CREATE TABLE IF NOT EXISTS capability_provider_calls (
  provider_call_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  provider_type TEXT NOT NULL,
  model TEXT,
  status TEXT NOT NULL,
  request_hash TEXT NOT NULL,
  response_hash TEXT,
  latency_ms NUMERIC,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_tool_calls (
  tool_call_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  tool_name TEXT NOT NULL,
  status TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  output_hash TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_memory_events (
  memory_event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  memory_id TEXT,
  event_type TEXT NOT NULL,
  eligible BOOLEAN NOT NULL DEFAULT false,
  affected_response BOOLEAN NOT NULL DEFAULT false,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_authorization_events (
  authorization_event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  actor_id TEXT,
  permission TEXT NOT NULL,
  allowed BOOLEAN NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_budget_ledger (
  budget_event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  event_type TEXT NOT NULL,
  amount NUMERIC NOT NULL DEFAULT 0,
  unit TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_recovery_events (
  recovery_event_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capability_result_artifacts (
  artifact_id TEXT PRIMARY KEY,
  attempt_id TEXT NOT NULL REFERENCES capability_attempts(attempt_id),
  artifact_type TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  uri TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

REVOKE DELETE ON capability_attempts FROM PUBLIC;
REVOKE DELETE ON capability_provider_calls FROM PUBLIC;
REVOKE DELETE ON capability_tool_calls FROM PUBLIC;
REVOKE DELETE ON capability_memory_events FROM PUBLIC;
REVOKE DELETE ON capability_authorization_events FROM PUBLIC;
REVOKE DELETE ON capability_budget_ledger FROM PUBLIC;
REVOKE DELETE ON capability_recovery_events FROM PUBLIC;
REVOKE DELETE ON capability_result_artifacts FROM PUBLIC;
