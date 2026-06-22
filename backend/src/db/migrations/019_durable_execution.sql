-- Durable workflow execution for Gate 3.

CREATE TABLE IF NOT EXISTS workflow_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'done', 'failed', 'blocked')),
    result JSONB,
    error TEXT,
    audit_log_id UUID,
    event_id UUID,
    action_attestation_id UUID REFERENCES action_attestations(action_id),
    claimed_by TEXT,
    retry_count INT NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_workflow_tasks_agent ON workflow_tasks(agent_id);
CREATE INDEX IF NOT EXISTS idx_workflow_tasks_status ON workflow_tasks(status, queued_at);
