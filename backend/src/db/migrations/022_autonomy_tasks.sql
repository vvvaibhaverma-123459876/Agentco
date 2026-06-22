-- Migration 022: Durable autonomy task infrastructure
--
-- Full autonomy task schema with complete state machine, tracing,
-- idempotency, and integration with calibration audit logs.

CREATE TABLE IF NOT EXISTS autonomy_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type TEXT NOT NULL CHECK (task_type IN (
        'goal_evaluation',
        'plan_execution',
        'plan_step_execution',
        'outcome_resolution',
        'memory_consolidation',
        'candidate_evaluation',
        'policy_update',
        'rollback',
        'custom'
    )),
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL CHECK (source IN ('system', 'agent', 'user', 'simulator')),
    source_id TEXT,
    created_by TEXT,
    assigned_agent_id TEXT,
    assigned_institution_id TEXT,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN (
        'created',
        'queued',
        'leased',
        'running',
        'waiting_for_tool',
        'waiting_for_memory',
        'waiting_for_human',
        'waiting_for_evaluation',
        'completed',
        'failed',
        'cancelled',
        'dead_lettered'
    )),
    priority INT NOT NULL DEFAULT 50 CHECK (priority >= 0 AND priority <= 100),
    risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    autonomy_level INT NOT NULL DEFAULT 0 CHECK (autonomy_level >= 0 AND autonomy_level <= 6),
    parent_task_id UUID REFERENCES autonomy_tasks(id),
    trace_id TEXT,
    run_id TEXT,
    idempotency_key TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,
    retry_count INT NOT NULL DEFAULT 0,
    max_retries INT NOT NULL DEFAULT 3,
    last_error TEXT,
    last_error_stack TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_autonomy_tasks_idempotency ON autonomy_tasks(idempotency_key)
    WHERE idempotency_key IS NOT NULL AND status NOT IN ('cancelled', 'dead_lettered');

CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_status ON autonomy_tasks(status, created_at);
CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_agent_id ON autonomy_tasks(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_parent_task_id ON autonomy_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_trace_id ON autonomy_tasks(trace_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_risk_level ON autonomy_tasks(risk_level);
CREATE INDEX IF NOT EXISTS idx_autonomy_tasks_created_at ON autonomy_tasks(created_at);


-- Track state transitions for audit trail
CREATE TABLE IF NOT EXISTS autonomy_task_events (
    id BIGSERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES autonomy_tasks(id),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'created',
        'queued',
        'leased',
        'started',
        'progress',
        'waiting',
        'completed',
        'failed',
        'cancelled',
        'retried',
        'human_intervention',
        'escalated'
    )),
    previous_status TEXT NOT NULL,
    new_status TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('system', 'agent', 'service', 'human', 'scheduler')),
    actor_id TEXT,
    reason TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_task_events_task_id ON autonomy_task_events(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_task_events_event_type ON autonomy_task_events(event_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_task_events_created_at ON autonomy_task_events(created_at);


-- Checkpoint for resuming interrupted tasks
CREATE TABLE IF NOT EXISTS autonomy_workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES autonomy_tasks(id),
    step_name TEXT NOT NULL,
    step_index INT NOT NULL,
    state_json JSONB NOT NULL,
    artifact_refs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    retry_count INT NOT NULL DEFAULT 0,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(task_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_autonomy_workflow_checkpoints_task_id ON autonomy_workflow_checkpoints(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_workflow_checkpoints_created_at ON autonomy_workflow_checkpoints(created_at);


-- Worker leasing for distributed execution
CREATE TABLE IF NOT EXISTS worker_leases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL UNIQUE REFERENCES autonomy_tasks(id),
    worker_id TEXT NOT NULL,
    worker_version TEXT,
    lease_acquired_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    lease_expires_at TIMESTAMPTZ NOT NULL,
    last_heartbeat_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    heartbeat_interval_seconds INT NOT NULL DEFAULT 30,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'released')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_worker_leases_task_id ON worker_leases(task_id);
CREATE INDEX IF NOT EXISTS idx_worker_leases_worker_id ON worker_leases(worker_id);
CREATE INDEX IF NOT EXISTS idx_worker_leases_expires_at ON worker_leases(lease_expires_at);
CREATE INDEX IF NOT EXISTS idx_worker_leases_status ON worker_leases(status);


-- Dead letter queue for failed tasks
CREATE TABLE IF NOT EXISTS autonomy_dead_letters (
    id BIGSERIAL PRIMARY KEY,
    task_id UUID REFERENCES autonomy_tasks(id),
    failure_type TEXT NOT NULL CHECK (failure_type IN (
        'timeout',
        'max_retries_exceeded',
        'fatal_error',
        'invalid_state',
        'dependency_failure',
        'resource_exhaustion',
        'policy_violation',
        'human_cancelled'
    )),
    error_message TEXT NOT NULL,
    error_code TEXT,
    stack_trace TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_state TEXT,
    attempts INT NOT NULL DEFAULT 0,
    requeue_eligible BOOLEAN NOT NULL DEFAULT false,
    requeue_reason TEXT,
    archived_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_dead_letters_task_id ON autonomy_dead_letters(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_dead_letters_failure_type ON autonomy_dead_letters(failure_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_dead_letters_created_at ON autonomy_dead_letters(created_at);


-- Helper: validate state transition
CREATE OR REPLACE FUNCTION validate_task_status_transition(
    p_current_status TEXT,
    p_new_status TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    -- Define valid transitions
    IF (p_current_status = 'created' AND p_new_status IN ('queued', 'cancelled')) THEN RETURN TRUE;
    ELSIF (p_current_status = 'queued' AND p_new_status IN ('leased', 'cancelled')) THEN RETURN TRUE;
    ELSIF (p_current_status = 'leased' AND p_new_status IN ('running', 'cancelled')) THEN RETURN TRUE;
    ELSIF (p_current_status = 'running' AND p_new_status IN (
        'waiting_for_tool', 'waiting_for_memory', 'waiting_for_human', 'waiting_for_evaluation',
        'completed', 'failed', 'cancelled'
    )) THEN RETURN TRUE;
    ELSIF (p_current_status LIKE 'waiting_%' AND p_new_status IN ('running', 'failed', 'cancelled')) THEN RETURN TRUE;
    ELSIF (p_current_status IN ('completed', 'failed', 'cancelled') AND p_new_status = 'dead_lettered') THEN RETURN TRUE;
    ELSE RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- Trigger: enforce valid status transitions and create events
CREATE OR REPLACE FUNCTION enforce_task_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status != OLD.status THEN
        -- Validate transition
        IF NOT validate_task_status_transition(OLD.status, NEW.status) THEN
            RAISE EXCEPTION 'Invalid task status transition from % to %', OLD.status, NEW.status;
        END IF;

        -- Update updated_at
        NEW.updated_at = now();

        -- Record status transition event
        INSERT INTO autonomy_task_events (
            task_id, event_type, previous_status, new_status,
            actor_type, reason, trace_id
        ) VALUES (
            NEW.id, 'status_change', OLD.status, NEW.status,
            'system', NEW.metadata->>'transition_reason', NEW.trace_id
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS autonomy_tasks_enforce_transitions ON autonomy_tasks;
CREATE TRIGGER autonomy_tasks_enforce_transitions
    BEFORE UPDATE ON autonomy_tasks
    FOR EACH ROW
    EXECUTE FUNCTION enforce_task_status_transition();
