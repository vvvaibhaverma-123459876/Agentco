-- Migration 021: Observability and traceability infrastructure
--
-- Adds comprehensive trace context, span tracking, and metrics storage
-- for all autonomy actions. Every major action carries trace_id, run_id,
-- task_id, policy_version, artifact_hash, etc.

CREATE TABLE IF NOT EXISTS trace_contexts (
    trace_id TEXT PRIMARY KEY,
    parent_trace_id TEXT,
    run_id TEXT NOT NULL,
    task_id UUID,
    parent_task_id UUID,
    agent_id TEXT,
    institution_id TEXT,
    society_id TEXT,
    model_version TEXT,
    prompt_version TEXT,
    policy_version TEXT,
    evaluator_version TEXT,
    artifact_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'failed')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_trace_contexts_run_id ON trace_contexts(run_id);
CREATE INDEX IF NOT EXISTS idx_trace_contexts_task_id ON trace_contexts(task_id);
CREATE INDEX IF NOT EXISTS idx_trace_contexts_agent_id ON trace_contexts(agent_id);
CREATE INDEX IF NOT EXISTS idx_trace_contexts_created_at ON trace_contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_trace_contexts_status ON trace_contexts(status);


CREATE TABLE IF NOT EXISTS spans (
    span_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES trace_contexts(trace_id),
    parent_span_id TEXT,
    span_name TEXT NOT NULL,
    span_type TEXT NOT NULL CHECK (span_type IN (
        'task_creation',
        'task_execution',
        'goal_selection',
        'plan_generation',
        'plan_execution',
        'tool_call',
        'memory_read',
        'memory_write',
        'perception_fetch',
        'prediction_registration',
        'resolution',
        'reward_calculation',
        'trajectory_write',
        'evaluation_run',
        'candidate_creation',
        'promotion_decision',
        'canary_deployment',
        'rollback',
        'human_override',
        'policy_evaluation',
        'governance_decision'
    )),
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'failed')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_ms BIGINT,
    error_message TEXT,
    error_stack_trace TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_spans_trace_id ON spans(trace_id);
CREATE INDEX IF NOT EXISTS idx_spans_span_type ON spans(span_type);
CREATE INDEX IF NOT EXISTS idx_spans_status ON spans(status);
CREATE INDEX IF NOT EXISTS idx_spans_created_at ON spans(created_at);


CREATE TABLE IF NOT EXISTS metrics (
    metric_id BIGSERIAL PRIMARY KEY,
    trace_id TEXT REFERENCES trace_contexts(trace_id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_type TEXT NOT NULL CHECK (metric_type IN ('counter', 'gauge', 'histogram')),
    metric_unit TEXT,
    labels JSONB NOT NULL DEFAULT '{}'::jsonb,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_metrics_trace_id ON metrics(trace_id);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);


CREATE TABLE IF NOT EXISTS metric_snapshots (
    snapshot_id BIGSERIAL PRIMARY KEY,
    snapshot_time TIMESTAMPTZ NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    time_window_seconds INT NOT NULL,
    aggregation_type TEXT NOT NULL CHECK (aggregation_type IN ('sum', 'avg', 'min', 'max', 'percentile')),
    aggregation_percentile INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_metric_snapshots_metric_name ON metric_snapshots(metric_name);
CREATE INDEX IF NOT EXISTS idx_metric_snapshots_snapshot_time ON metric_snapshots(snapshot_time);


-- Structured logs with full trace context
CREATE TABLE IF NOT EXISTS structured_logs (
    log_id BIGSERIAL PRIMARY KEY,
    trace_id TEXT REFERENCES trace_contexts(trace_id),
    span_id TEXT REFERENCES spans(span_id),
    task_id UUID,
    log_level TEXT NOT NULL CHECK (log_level IN ('debug', 'info', 'warn', 'error')),
    log_message TEXT NOT NULL,
    log_type TEXT,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    stack_trace TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    indexed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_structured_logs_trace_id ON structured_logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_structured_logs_task_id ON structured_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_structured_logs_log_level ON structured_logs(log_level);
CREATE INDEX IF NOT EXISTS idx_structured_logs_created_at ON structured_logs(created_at);


-- Audit events linked to traces
CREATE TABLE IF NOT EXISTS trace_audit_events (
    audit_id BIGSERIAL PRIMARY KEY,
    trace_id TEXT NOT NULL REFERENCES trace_contexts(trace_id),
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    reason TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'error', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trace_audit_events_trace_id ON trace_audit_events(trace_id);
CREATE INDEX IF NOT EXISTS idx_trace_audit_events_actor_id ON trace_audit_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_trace_audit_events_event_type ON trace_audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_trace_audit_events_created_at ON trace_audit_events(created_at);


-- Immutable: trace contexts cannot be modified after creation
CREATE TRIGGER trace_contexts_immutable_after_created
    BEFORE UPDATE ON trace_contexts
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('trace_contexts');


-- Helper function to begin trace context
CREATE OR REPLACE FUNCTION begin_trace(
    p_run_id TEXT,
    p_task_id UUID DEFAULT NULL,
    p_agent_id TEXT DEFAULT NULL,
    p_institution_id TEXT DEFAULT NULL,
    p_policy_version TEXT DEFAULT NULL,
    p_model_version TEXT DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_trace_id TEXT;
BEGIN
    v_trace_id := 'trace_' || gen_random_uuid()::TEXT;

    INSERT INTO trace_contexts (
        trace_id, run_id, task_id, agent_id, institution_id,
        policy_version, model_version, status
    ) VALUES (
        v_trace_id, p_run_id, p_task_id, p_agent_id, p_institution_id,
        p_policy_version, p_model_version, 'active'
    );

    RETURN v_trace_id;
END;
$$ LANGUAGE plpgsql;


-- Helper function to end trace context
CREATE OR REPLACE FUNCTION end_trace(
    p_trace_id TEXT,
    p_status TEXT DEFAULT 'completed'
) RETURNS VOID AS $$
BEGIN
    UPDATE trace_contexts
    SET status = p_status, completed_at = now()
    WHERE trace_id = p_trace_id;
END;
$$ LANGUAGE plpgsql;


-- Helper function to record span
CREATE OR REPLACE FUNCTION record_span(
    p_trace_id TEXT,
    p_span_name TEXT,
    p_span_type TEXT,
    p_status TEXT,
    p_duration_ms BIGINT DEFAULT NULL,
    p_error_message TEXT DEFAULT NULL,
    p_attributes JSONB DEFAULT NULL,
    p_metrics JSONB DEFAULT NULL
) RETURNS TEXT AS $$
DECLARE
    v_span_id TEXT;
BEGIN
    v_span_id := 'span_' || gen_random_uuid()::TEXT;

    INSERT INTO spans (
        span_id, trace_id, span_name, span_type, status,
        duration_ms, error_message, attributes, metrics
    ) VALUES (
        v_span_id, p_trace_id, p_span_name, p_span_type, p_status,
        p_duration_ms, p_error_message, COALESCE(p_attributes, '{}'::jsonb),
        COALESCE(p_metrics, '{}'::jsonb)
    );

    RETURN v_span_id;
END;
$$ LANGUAGE plpgsql;


-- Helper function to record metric
CREATE OR REPLACE FUNCTION record_metric(
    p_trace_id TEXT,
    p_metric_name TEXT,
    p_metric_value FLOAT,
    p_metric_type TEXT,
    p_metric_unit TEXT DEFAULT NULL,
    p_labels JSONB DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    INSERT INTO metrics (
        trace_id, metric_name, metric_value, metric_type, metric_unit, labels
    ) VALUES (
        p_trace_id, p_metric_name, p_metric_value, p_metric_type,
        p_metric_unit, COALESCE(p_labels, '{}'::jsonb)
    );
END;
$$ LANGUAGE plpgsql;
