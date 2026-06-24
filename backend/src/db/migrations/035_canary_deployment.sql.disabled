-- Migration 032: Canary deployment and rollback
--
-- Safe promotion workflow: passing eval → canary at low % → gradual ramp →
-- auto-halt on regression → rollback if needed.

CREATE TABLE IF NOT EXISTS canary_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    target_service TEXT NOT NULL,
    initial_percentage INT NOT NULL CHECK (initial_percentage > 0 AND initial_percentage <= 100),
    max_percentage INT NOT NULL CHECK (max_percentage >= initial_percentage AND max_percentage <= 100),
    increment_percentage INT NOT NULL DEFAULT 10 CHECK (increment_percentage > 0),
    increment_interval_minutes INT NOT NULL DEFAULT 5,
    success_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'active',
        'paused',
        'completed',
        'rolled_back',
        'halted'
    )),
    halt_reason TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_canary_plans_artifact_id ON canary_plans(artifact_id);
CREATE INDEX IF NOT EXISTS idx_canary_plans_status ON canary_plans(status);
CREATE INDEX IF NOT EXISTS idx_canary_plans_created_at ON canary_plans(created_at);


-- Observations during canary run
CREATE TABLE IF NOT EXISTS canary_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id UUID NOT NULL REFERENCES canary_plans(id),
    observation_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_type TEXT NOT NULL CHECK (metric_type IN ('counter', 'gauge', 'histogram')),
    threshold FLOAT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'warning')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canary_observations_canary_plan_id ON canary_observations(canary_plan_id);
CREATE INDEX IF NOT EXISTS idx_canary_observations_metric_name ON canary_observations(metric_name);
CREATE INDEX IF NOT EXISTS idx_canary_observations_status ON canary_observations(status);


-- Rollback events
CREATE TABLE IF NOT EXISTS rollback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    previous_artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    reason TEXT NOT NULL CHECK (reason IN (
        'safety_regression',
        'performance_regression',
        'manual_request',
        'canary_failure',
        'resource_exhaustion',
        'user_request',
        'other'
    )),
    triggered_by TEXT NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_rollback_events_artifact_id ON rollback_events(artifact_id);
CREATE INDEX IF NOT EXISTS idx_rollback_events_reason ON rollback_events(reason);
CREATE INDEX IF NOT EXISTS idx_rollback_events_created_at ON rollback_events(created_at);


-- Helper: check canary metrics
CREATE OR REPLACE FUNCTION check_canary_metrics(
    p_canary_plan_id UUID
) RETURNS TABLE(should_halt BOOLEAN, halt_reason TEXT, passed_count INT, failed_count INT) AS $$
DECLARE
    v_failed_count INT;
    v_passed_count INT;
BEGIN
    SELECT COUNT(*) FILTER (WHERE status = 'fail') INTO v_failed_count
    FROM canary_observations WHERE canary_plan_id = p_canary_plan_id;

    SELECT COUNT(*) FILTER (WHERE status = 'pass') INTO v_passed_count
    FROM canary_observations WHERE canary_plan_id = p_canary_plan_id;

    RETURN QUERY SELECT
        v_failed_count > 0,
        CASE WHEN v_failed_count > 0 THEN 'Safety metrics failed' ELSE NULL END,
        v_passed_count,
        v_failed_count;
END;
$$ LANGUAGE plpgsql;
