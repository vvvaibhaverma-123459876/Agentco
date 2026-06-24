-- Migration 025: Goal Management Infrastructure (Clean Consolidated Version)
--
-- Consolidates all goal-related tables from Phases 5-8:
-- - Phase 5: Goal management
-- - Phase 6: Planning
-- - Phase 7: Outcomes
-- - Phase 8: Rewards, Evaluation
--
-- CRITICAL: This migration is self-contained. No dependencies on external type definitions.
-- All types, tables, indexes, and triggers defined here.

-- Clean slate: drop all tables and types that may exist from previous incomplete migrations
DROP TABLE IF EXISTS eval_scorecards CASCADE;
DROP TABLE IF EXISTS eval_failures CASCADE;
DROP TABLE IF EXISTS eval_results CASCADE;
DROP TABLE IF EXISTS eval_runs CASCADE;
DROP TABLE IF EXISTS eval_cases CASCADE;
DROP TABLE IF EXISTS eval_suites CASCADE;
DROP TABLE IF EXISTS reward_audit CASCADE;
DROP TABLE IF EXISTS reward_calculations CASCADE;
DROP TABLE IF EXISTS reward_functions CASCADE;
DROP TABLE IF EXISTS autonomy_outcomes CASCADE;
DROP TABLE IF EXISTS plan_status_events CASCADE;
DROP TABLE IF EXISTS plan_reviews CASCADE;
DROP TABLE IF EXISTS autonomy_plan_steps CASCADE;
DROP TABLE IF EXISTS autonomy_plans CASCADE;
DROP TABLE IF EXISTS goal_status_events CASCADE;
DROP TABLE IF EXISTS goal_reviews CASCADE;
DROP TABLE IF EXISTS goal_budgets CASCADE;
DROP TABLE IF EXISTS goal_conflicts CASCADE;
DROP TABLE IF EXISTS goal_evidence CASCADE;
DROP TABLE IF EXISTS autonomy_goals CASCADE;
DROP TYPE IF EXISTS plan_step_status CASCADE;
DROP TYPE IF EXISTS plan_status CASCADE;
DROP TYPE IF EXISTS risk_level CASCADE;
DROP TYPE IF EXISTS autonomy_level CASCADE;
DROP TYPE IF EXISTS goal_status CASCADE;

-- ============================================================
-- TYPE DEFINITIONS
-- ============================================================

DROP TYPE IF EXISTS goal_status CASCADE;
CREATE TYPE goal_status AS ENUM (
    'proposed', 'under_review', 'approved', 'rejected',
    'active', 'blocked', 'paused', 'completed', 'retired'
);

DROP TYPE IF EXISTS autonomy_level CASCADE;
CREATE TYPE autonomy_level AS ENUM (
    'L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'
);

DROP TYPE IF EXISTS risk_level CASCADE;
CREATE TYPE risk_level AS ENUM (
    'critical', 'high', 'medium', 'low'
);

DROP TYPE IF EXISTS plan_status CASCADE;
CREATE TYPE plan_status AS ENUM (
    'draft', 'validating', 'review_required', 'approved',
    'active', 'paused', 'completed', 'failed', 'retired'
);

DROP TYPE IF EXISTS plan_step_status CASCADE;
CREATE TYPE plan_step_status AS ENUM (
    'pending', 'ready', 'running', 'completed',
    'failed', 'skipped', 'blocked'
);

-- ============================================================
-- PHASE 5: GOAL MANAGEMENT TABLES
-- ============================================================

DROP TABLE IF EXISTS autonomy_goals CASCADE;
CREATE TABLE autonomy_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL CHECK (source IN ('agent_proposed', 'perception_derived', 'governance_mandated', 'manual')),
    proposed_by TEXT NOT NULL,
    owning_agent_id UUID,
    owning_institution_id UUID,
    domain TEXT NOT NULL,
    expected_value NUMERIC(12, 2),
    risk_level risk_level NOT NULL DEFAULT 'medium',
    autonomy_level_allowed autonomy_level NOT NULL DEFAULT 'L2',
    status goal_status NOT NULL DEFAULT 'proposed',
    parent_goal_id UUID REFERENCES autonomy_goals(id),
    success_criteria_json JSONB DEFAULT '{}'::jsonb,
    stop_conditions_json JSONB DEFAULT '{}'::jsonb,
    simulation_derived BOOLEAN DEFAULT false,
    trace_id TEXT,
    run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    paused_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ
);

CREATE INDEX idx_autonomy_goals_status ON autonomy_goals(status);
CREATE INDEX idx_autonomy_goals_domain ON autonomy_goals(domain);
CREATE INDEX idx_autonomy_goals_risk_level ON autonomy_goals(risk_level);
CREATE INDEX idx_autonomy_goals_owning_agent ON autonomy_goals(owning_agent_id);
CREATE INDEX idx_autonomy_goals_owning_institution ON autonomy_goals(owning_institution_id);
CREATE INDEX idx_autonomy_goals_parent ON autonomy_goals(parent_goal_id);
CREATE INDEX idx_autonomy_goals_simulation ON autonomy_goals(simulation_derived);

CREATE TABLE goal_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    evidence_type TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    evidence_hash TEXT,
    relevance_score FLOAT CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    provenance_json JSONB DEFAULT '{}'::jsonb,
    simulation_derived BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goal_evidence_goal_id ON goal_evidence(goal_id);
CREATE INDEX idx_goal_evidence_type ON goal_evidence(evidence_type);

CREATE TABLE goal_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflicting_goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflict_type TEXT NOT NULL,
    severity risk_level DEFAULT 'medium',
    resolution_status TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goal_conflicts_goal_id ON goal_conflicts(goal_id);
CREATE INDEX idx_goal_conflicts_conflicting_goal_id ON goal_conflicts(conflicting_goal_id);

CREATE TABLE goal_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL UNIQUE REFERENCES autonomy_goals(id),
    compute_budget BIGINT,
    token_budget BIGINT,
    time_budget_seconds BIGINT,
    tool_budget_json JSONB DEFAULT '{}'::jsonb,
    spend_limit NUMERIC(12, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goal_budgets_goal_id ON goal_budgets(goal_id);

CREATE TABLE goal_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    reviewer_id TEXT NOT NULL,
    reviewer_role TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'conditional', 'deferred')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goal_reviews_goal_id ON goal_reviews(goal_id);
CREATE INDEX idx_goal_reviews_reviewer_id ON goal_reviews(reviewer_id);

CREATE TABLE goal_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    previous_status goal_status,
    new_status goal_status NOT NULL,
    actor_type TEXT NOT NULL,
    actor_id TEXT,
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_goal_status_events_goal_id ON goal_status_events(goal_id);
CREATE INDEX idx_goal_status_events_new_status ON goal_status_events(new_status);
CREATE INDEX idx_goal_status_events_created_at ON goal_status_events(created_at);

-- ============================================================
-- PHASE 6: PLANNING TABLES
-- ============================================================

CREATE TABLE autonomy_plans (
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

CREATE INDEX idx_autonomy_plans_goal_id ON autonomy_plans(goal_id);
CREATE INDEX idx_autonomy_plans_status ON autonomy_plans(status);
CREATE INDEX idx_autonomy_plans_risk_level ON autonomy_plans(risk_level);

CREATE TABLE autonomy_plan_steps (
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

CREATE INDEX idx_autonomy_plan_steps_plan_id ON autonomy_plan_steps(plan_id);
CREATE INDEX idx_autonomy_plan_steps_status ON autonomy_plan_steps(status);

CREATE TABLE plan_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES autonomy_plans(id),
    reviewer_id TEXT NOT NULL,
    review_type TEXT,
    decision TEXT NOT NULL,
    issues_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plan_status_events (
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

CREATE INDEX idx_plan_status_events_plan_id ON plan_status_events(plan_id);

-- ============================================================
-- PHASE 7: OUTCOME TABLES
-- ============================================================

CREATE TABLE autonomy_outcomes (
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

CREATE INDEX idx_autonomy_outcomes_goal_id ON autonomy_outcomes(goal_id);
CREATE INDEX idx_autonomy_outcomes_plan_id ON autonomy_outcomes(plan_id);
CREATE INDEX idx_autonomy_outcomes_task_id ON autonomy_outcomes(task_id);

-- ============================================================
-- PHASE 8: EVALUATION & REWARDS TABLES
-- ============================================================

CREATE TABLE eval_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    domain TEXT,
    version INT DEFAULT 1,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_suites_name ON eval_suites(name);
CREATE INDEX idx_eval_suites_domain ON eval_suites(domain);

CREATE TABLE eval_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    case_name TEXT NOT NULL,
    description TEXT,
    input_data JSONB,
    expected_output JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_cases_suite_id ON eval_cases(suite_id);

CREATE TABLE eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    run_timestamp TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'running',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_runs_suite_id ON eval_runs(suite_id);
CREATE INDEX idx_eval_runs_status ON eval_runs(status);

CREATE TABLE eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    case_id UUID NOT NULL REFERENCES eval_cases(id),
    actual_output JSONB,
    passed BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_results_eval_run_id ON eval_results(eval_run_id);

CREATE TABLE eval_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    case_id UUID NOT NULL REFERENCES eval_cases(id),
    failure_reason TEXT,
    actual_output JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_failures_eval_run_id ON eval_failures(eval_run_id);

CREATE TABLE eval_scorecards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    autonomy_score FLOAT,
    safety_score FLOAT,
    calibration_score FLOAT,
    planning_score FLOAT,
    memory_score FLOAT,
    tool_score FLOAT,
    reward_score FLOAT,
    regression_score FLOAT,
    promotion_eligible BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_scorecards_eval_run_id ON eval_scorecards(eval_run_id);
CREATE INDEX idx_eval_scorecards_promotion_eligible ON eval_scorecards(promotion_eligible);

CREATE TABLE reward_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    function_type TEXT NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reward_functions_name ON reward_functions(name);

CREATE TABLE reward_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    function_id UUID NOT NULL REFERENCES reward_functions(id),
    outcome_id UUID,
    reward_value FLOAT NOT NULL,
    metrics_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reward_calculations_function_id ON reward_calculations(function_id);
CREATE INDEX idx_reward_calculations_outcome_id ON reward_calculations(outcome_id);

CREATE TABLE reward_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    function_id UUID NOT NULL REFERENCES reward_functions(id),
    event_type TEXT NOT NULL,
    event_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reward_audit_function_id ON reward_audit(function_id);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS goal_evidence_immutable ON goal_evidence;
CREATE TRIGGER goal_evidence_immutable
    BEFORE UPDATE ON goal_evidence
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('goal_evidence');

DROP TRIGGER IF EXISTS goal_status_events_immutable ON goal_status_events;
CREATE TRIGGER goal_status_events_immutable
    BEFORE UPDATE ON goal_status_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('goal_status_events');

DROP TRIGGER IF EXISTS eval_results_immutable ON eval_results;
CREATE TRIGGER eval_results_immutable
    BEFORE UPDATE ON eval_results
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('eval_results');

DROP TRIGGER IF EXISTS eval_failures_immutable ON eval_failures;
CREATE TRIGGER eval_failures_immutable
    BEFORE UPDATE ON eval_failures
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('eval_failures');

DROP TRIGGER IF EXISTS goal_prevent_deletion ON autonomy_goals;
CREATE TRIGGER goal_prevent_deletion
    BEFORE DELETE ON autonomy_goals
    FOR EACH ROW
    WHEN (OLD.status IN ('completed', 'retired'))
    EXECUTE FUNCTION raise_immutability_violation('autonomy_goals completed/retired cannot delete');
