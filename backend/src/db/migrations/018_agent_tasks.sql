-- Durable agent task dispatch.

CREATE TABLE IF NOT EXISTS agent_tasks (
    task_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN (
        'queued',
        'leased',
        'running',
        'succeeded',
        'failed',
        'cancelled',
        'dead_letter'
    )),
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    leased_at TIMESTAMPTZ,
    lease_owner TEXT,
    lease_expires_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    correlation_id TEXT,
    audit_event_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_status
    ON agent_tasks (status, queued_at);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent
    ON agent_tasks (agent_id, queued_at DESC);

CREATE TABLE IF NOT EXISTS agent_task_events (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES agent_tasks(task_id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_task_events_task
    ON agent_task_events (task_id, created_at);

CREATE OR REPLACE FUNCTION prevent_agent_task_event_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'agent_task_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_agent_task_events_append_only ON agent_task_events;
CREATE TRIGGER trg_agent_task_events_append_only
    BEFORE UPDATE OR DELETE ON agent_task_events
    FOR EACH ROW
    EXECUTE FUNCTION prevent_agent_task_event_mutation();
