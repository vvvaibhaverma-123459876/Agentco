-- Migration 026: Durable planning and decomposition
--
-- Plans break goals into executable steps with dependencies, checkpoints,
-- and version control.

CREATE TABLE IF NOT EXISTS autonomy_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    task_id UUID REFERENCES autonomy_tasks(id),
    planner_agent_id TEXT,
    plan_version TEXT NOT NULL DEFAULT '1.0',
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft',
        'pending_review',
        'approved',
        'active',
        'paused',
        'completed',
        'failed',
        'cancelled',
        'archived'
    )),
    horizon INT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    success_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    stop_conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_autonomy_plans_goal_id ON autonomy_plans(goal_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_plans_task_id ON autonomy_plans(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_plans_status ON autonomy_plans(status);
CREATE INDEX IF NOT EXISTS idx_autonomy_plans_created_at ON autonomy_plans(created_at);


-- Individual plan steps with DAG structure
CREATE TABLE IF NOT EXISTS autonomy_plan_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    step_index INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    required_tools_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    expected_output_schema JSONB,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'queued',
        'running',
        'waiting_for_approval',
        'completed',
        'failed',
        'skipped',
        'recovered'
    )),
    depends_on_step_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    checkpoint_required BOOLEAN NOT NULL DEFAULT false,
    max_retries INT NOT NULL DEFAULT 3,
    timeout_seconds INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(plan_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_autonomy_plan_steps_plan_id ON autonomy_plan_steps(plan_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_plan_steps_status ON autonomy_plan_steps(status);


-- Plan reviews and approvals
CREATE TABLE IF NOT EXISTS plan_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    reviewer_id TEXT NOT NULL,
    review_type TEXT NOT NULL CHECK (review_type IN (
        'feasibility',
        'safety',
        'resource_validation',
        'dependency_check',
        'governance_approval'
    )),
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'needs_revision')),
    issues_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommendations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plan_reviews_plan_id ON plan_reviews(plan_id);
CREATE INDEX IF NOT EXISTS idx_plan_reviews_reviewer_id ON plan_reviews(reviewer_id);


-- Helper: validate step DAG
CREATE OR REPLACE FUNCTION validate_step_dag(
    p_plan_id UUID
) RETURNS TABLE(valid BOOLEAN, error_message TEXT) AS $$
DECLARE
    v_step_id UUID;
    v_depends_on_ids UUID[];
    v_max_step_index INT;
BEGIN
    SELECT MAX(step_index) INTO v_max_step_index
    FROM autonomy_plan_steps WHERE plan_id = p_plan_id;

    FOR v_step_id, v_depends_on_ids IN
        SELECT id, depends_on_step_ids
        FROM autonomy_plan_steps
        WHERE plan_id = p_plan_id
    LOOP
        -- Check all dependencies exist
        IF EXISTS (
            SELECT 1 FROM UNNEST(v_depends_on_ids) AS dep_id
            WHERE NOT EXISTS (
                SELECT 1 FROM autonomy_plan_steps WHERE id = dep_id AND plan_id = p_plan_id
            )
        ) THEN
            RETURN QUERY SELECT false, 'Dependency not found for step: ' || v_step_id::TEXT;
            RETURN;
        END IF;
    END LOOP;

    RETURN QUERY SELECT true, NULL;
END;
$$ LANGUAGE plpgsql;


-- Helper: check if plan requires long-horizon review
CREATE OR REPLACE FUNCTION plan_requires_long_horizon_review(
    p_plan_id UUID,
    p_horizon_threshold INT DEFAULT 100
) RETURNS BOOLEAN AS $$
DECLARE
    v_horizon INT;
BEGIN
    SELECT horizon INTO v_horizon FROM autonomy_plans WHERE id = p_plan_id;
    RETURN COALESCE(v_horizon, 0) > p_horizon_threshold;
END;
$$ LANGUAGE plpgsql;
