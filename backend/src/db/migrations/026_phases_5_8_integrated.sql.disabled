-- Migration 026: Phases 5-8 Integrated Implementation
-- Goal Management, Planning, Outcomes/Rewards, and Evaluation Harness
--
-- This migration establishes the complete autonomy control loop:
-- perception_event → goal → plan → outcome → reward → eval → scorecard

-- ============================================================
-- PHASE 5: Goal Management and Autonomy Levels
-- ============================================================
-- NOTE: autonomy_level, goal_status, and risk_level types are
-- created in migration 025_goal_management.sql (or similar).
-- These statements are here for documentation but DO NOT recreate.

-- Goal-related tables (autonomy_goals, goal_evidence, goal_conflicts, goal_budgets, goal_reviews, goal_status_events)
-- are defined in migration 025_goal_management.sql - do NOT duplicate them here

-- ============================================================
-- PHASE 6: Planning and Long-Horizon Task Decomposition
-- ============================================================

CREATE TYPE plan_status AS ENUM (
    'draft',
    'validating',
    'review_required',
    'approved',
    'active',
    'paused',
    'completed',
    'failed',
    'retired'
);

CREATE TYPE plan_step_status AS ENUM (
    'pending',
    'ready',
    'running',
    'completed',
    'failed',
    'skipped',
    'blocked'
);

-- Plans table
CREATE TABLE IF NOT EXISTS autonomy_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    task_id UUID,
    planner_agent_id TEXT,
    plan_version INT DEFAULT 1,
    status plan_status NOT NULL DEFAULT 'draft',
    horizon INT,
    risk_level risk_level DEFAULT 'medium',
    success_criteria_json JSONB DEFAULT '{}'::jsonb,
    stop_conditions_json JSONB DEFAULT '{}'::jsonb,
    trace_id TEXT,
    run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_autonomy_plans_goal_id ON autonomy_plans(goal_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_plans_status ON autonomy_plans(status);
CREATE INDEX IF NOT EXISTS idx_autonomy_plans_risk_level ON autonomy_plans(risk_level);

-- Plan steps
CREATE TABLE IF NOT EXISTS autonomy_plan_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    step_index INT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    required_tools_json JSONB DEFAULT '{}'::jsonb,
    expected_output_schema JSONB,
    risk_level risk_level DEFAULT 'medium',
    status plan_step_status NOT NULL DEFAULT 'pending',
    depends_on_step_ids UUID[] DEFAULT ARRAY[]::UUID[],
    checkpoint_required BOOLEAN DEFAULT false,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_autonomy_plan_steps_plan_id ON autonomy_plan_steps(plan_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_plan_steps_status ON autonomy_plan_steps(status);

-- Plan reviews
CREATE TABLE IF NOT EXISTS plan_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    reviewer_id TEXT NOT NULL,
    review_type TEXT,
    decision TEXT NOT NULL,
    issues_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Plan status events
CREATE TABLE IF NOT EXISTS plan_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    previous_status plan_status,
    new_status plan_status NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plan_status_events_plan_id ON plan_status_events(plan_id);

-- ============================================================
-- PHASE 7: Outcome Resolution and Reward Calculation
-- ============================================================

-- Outcomes table
CREATE TABLE IF NOT EXISTS autonomy_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID,
    goal_id UUID REFERENCES autonomy_goals(id),
    plan_id UUID REFERENCES autonomy_plans(id),
    episode_id UUID,
    outcome_type TEXT NOT NULL,
    outcome_status TEXT DEFAULT 'pending',
    objective_result_json JSONB DEFAULT '{}'::jsonb,
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    evidence_refs_json JSONB DEFAULT '[]'::jsonb,
    simulation_derived BOOLEAN DEFAULT false,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_goal_id ON autonomy_outcomes(goal_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_plan_id ON autonomy_outcomes(plan_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_status ON autonomy_outcomes(outcome_status);

-- Reward functions (versioned, not modifiable)
CREATE TABLE IF NOT EXISTS reward_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    version INT NOT NULL,
    formula_json JSONB NOT NULL,
    owner TEXT,
    risk_level risk_level DEFAULT 'medium',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(name, domain, version)
);

CREATE INDEX IF NOT EXISTS idx_reward_functions_name_version ON reward_functions(name, version);
CREATE INDEX IF NOT EXISTS idx_reward_functions_active ON reward_functions(active);

-- Reward calculations (persisted, immutable)
CREATE TABLE IF NOT EXISTS reward_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES autonomy_outcomes(id),
    reward_function_id UUID NOT NULL REFERENCES reward_functions(id),
    reward_score FLOAT,
    regret_score FLOAT,
    calculation_details_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reward_calculations_outcome_id ON reward_calculations(outcome_id);

-- Reward audit
CREATE TABLE IF NOT EXISTS reward_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reward_calculation_id UUID NOT NULL REFERENCES reward_calculations(id),
    reviewer_id TEXT,
    decision TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- PHASE 8: Evaluation Harness and Scorecards
-- ============================================================

-- Eval suites
CREATE TABLE IF NOT EXISTS eval_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    domain TEXT,
    version INT DEFAULT 1,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Eval cases
CREATE TABLE IF NOT EXISTS eval_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    name TEXT NOT NULL,
    case_type TEXT NOT NULL,
    input_json JSONB,
    expected_json JSONB,
    scoring_config_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_id ON eval_cases(suite_id);

-- Eval runs
CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    target_type TEXT,
    target_id UUID,
    run_status TEXT DEFAULT 'pending',
    baseline_ref TEXT,
    candidate_ref TEXT,
    trace_id TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_suite_id ON eval_runs(suite_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(run_status);

-- Eval results
CREATE TABLE IF NOT EXISTS eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    case_id UUID NOT NULL REFERENCES eval_cases(id),
    status TEXT,
    score FLOAT,
    details_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_eval_run_id ON eval_results(eval_run_id);

-- Eval failures
CREATE TABLE IF NOT EXISTS eval_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    case_id UUID REFERENCES eval_cases(id),
    failure_type TEXT,
    failure_message TEXT,
    severity risk_level DEFAULT 'high',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Eval scorecards (computed from real data, not hardcoded)
CREATE TABLE IF NOT EXISTS eval_scorecards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL UNIQUE REFERENCES eval_runs(id),
    autonomy_score FLOAT,
    safety_score FLOAT,
    calibration_score FLOAT,
    planning_score FLOAT,
    memory_score FLOAT,
    tool_score FLOAT,
    reward_score FLOAT,
    regression_score FLOAT,
    promotion_eligible BOOLEAN DEFAULT false,
    decision_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_scorecards_promotion_eligible ON eval_scorecards(promotion_eligible);

-- ============================================================
-- Immutability and Audit Enforcement
-- ============================================================
-- NOTE: goal_status_events_immutable and goal_evidence_immutable triggers
-- are already created in migration 025_goal_management.sql

DROP TRIGGER IF EXISTS plan_status_events_immutable ON plan_status_events;
CREATE TRIGGER plan_status_events_immutable
    BEFORE UPDATE ON plan_status_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('plan_status_events');

DROP TRIGGER IF EXISTS reward_calculations_immutable ON reward_calculations;
CREATE TRIGGER reward_calculations_immutable
    BEFORE UPDATE ON reward_calculations
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('reward_calculations');

DROP TRIGGER IF EXISTS eval_results_immutable ON eval_results;
CREATE TRIGGER eval_results_immutable
    BEFORE UPDATE ON eval_results
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('eval_results');

DROP TRIGGER IF EXISTS eval_scorecards_immutable ON eval_scorecards;
CREATE TRIGGER eval_scorecards_immutable
    BEFORE UPDATE ON eval_scorecards
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('eval_scorecards');

-- ============================================================
-- View for integrated query support
-- ============================================================

CREATE VIEW goal_to_eval_lineage AS
    SELECT
        g.id as goal_id,
        g.title as goal_title,
        g.risk_level as goal_risk,
        p.id as plan_id,
        p.status as plan_status,
        o.id as outcome_id,
        o.outcome_status,
        rc.reward_score,
        es.name as eval_suite,
        sc.autonomy_score,
        sc.safety_score,
        sc.promotion_eligible,
        g.trace_id
    FROM autonomy_goals g
    LEFT JOIN autonomy_plans p ON p.goal_id = g.id
    LEFT JOIN autonomy_outcomes o ON o.goal_id = g.id
    LEFT JOIN reward_calculations rc ON rc.outcome_id = o.id
    LEFT JOIN eval_runs er ON er.target_id = g.id
    LEFT JOIN eval_suites es ON es.id = er.suite_id
    LEFT JOIN eval_scorecards sc ON sc.eval_run_id = er.id;
