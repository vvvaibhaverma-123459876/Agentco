-- Migration 028: Autonomy evaluation harness
--
-- Eval suites for planning, tool use, memory, safety, autonomy, and
-- self-modification. Promotion decision gating.

CREATE TABLE IF NOT EXISTS eval_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    eval_type TEXT NOT NULL CHECK (eval_type IN (
        'planning',
        'tool_use',
        'memory',
        'safety',
        'autonomy',
        'self_modification',
        'regression',
        'custom'
    )),
    description TEXT,
    total_cases INT NOT NULL,
    created_by TEXT,
    version TEXT NOT NULL DEFAULT '1.0',
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_suites_eval_type ON eval_suites(eval_type);
CREATE INDEX IF NOT EXISTS idx_eval_suites_active ON eval_suites(active);


-- Individual eval cases
CREATE TABLE IF NOT EXISTS eval_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    case_index INT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    input_json JSONB NOT NULL,
    expected_output_json JSONB NOT NULL,
    acceptance_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(suite_id, case_index)
);

CREATE INDEX IF NOT EXISTS idx_eval_cases_suite_id ON eval_cases(suite_id);


-- Eval run results
CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    suite_id UUID NOT NULL REFERENCES eval_suites(id),
    policy_version TEXT,
    model_version TEXT,
    prompt_version TEXT,
    evaluator_version TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    total_cases INT NOT NULL,
    passed_cases INT NOT NULL DEFAULT 0,
    failed_cases INT NOT NULL DEFAULT 0,
    skipped_cases INT NOT NULL DEFAULT 0,
    pass_rate FLOAT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_suite_id ON eval_runs(suite_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status);
CREATE INDEX IF NOT EXISTS idx_eval_runs_created_at ON eval_runs(created_at);


-- Individual case results
CREATE TABLE IF NOT EXISTS eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    case_id UUID NOT NULL REFERENCES eval_cases(id),
    passed BOOLEAN NOT NULL,
    score FLOAT CHECK (score >= 0.0 AND score <= 1.0),
    actual_output_json JSONB,
    error_message TEXT,
    error_trace TEXT,
    reasoning TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_eval_run_id ON eval_results(eval_run_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_case_id ON eval_results(case_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_passed ON eval_results(passed);


-- Eval failures tracked for analysis
CREATE TABLE IF NOT EXISTS eval_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_result_id UUID NOT NULL REFERENCES eval_results(id),
    failure_category TEXT NOT NULL CHECK (failure_category IN (
        'correctness',
        'safety',
        'performance',
        'hallucination',
        'policy_violation',
        'timeout',
        'resource_exhaustion',
        'unknown'
    )),
    root_cause TEXT,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_failures_eval_result_id ON eval_failures(eval_result_id);
CREATE INDEX IF NOT EXISTS idx_eval_failures_failure_category ON eval_failures(failure_category);


-- Autonomy scorecard
CREATE TABLE IF NOT EXISTS eval_scorecards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    autonomy_score FLOAT CHECK (autonomy_score >= 0.0 AND autonomy_score <= 1.0),
    safety_score FLOAT CHECK (safety_score >= 0.0 AND safety_score <= 1.0),
    calibration_score FLOAT CHECK (calibration_score >= 0.0 AND calibration_score <= 1.0),
    planning_score FLOAT CHECK (planning_score >= 0.0 AND planning_score <= 1.0),
    memory_score FLOAT CHECK (memory_score >= 0.0 AND memory_score <= 1.0),
    tool_score FLOAT CHECK (tool_score >= 0.0 AND tool_score <= 1.0),
    regression_score FLOAT CHECK (regression_score >= 0.0 AND regression_score <= 1.0),
    overall_score FLOAT CHECK (overall_score >= 0.0 AND overall_score <= 1.0),
    promotion_eligible BOOLEAN NOT NULL DEFAULT false,
    promotion_threshold FLOAT NOT NULL DEFAULT 0.80,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_scorecards_eval_run_id ON eval_scorecards(eval_run_id);
CREATE INDEX IF NOT EXISTS idx_eval_scorecards_promotion_eligible ON eval_scorecards(promotion_eligible);


-- Regression detection: compare against baseline
CREATE OR REPLACE FUNCTION check_regression(
    p_eval_run_id UUID,
    p_baseline_run_id UUID,
    p_regression_threshold FLOAT DEFAULT 0.05
) RETURNS TABLE(has_regression BOOLEAN, score_delta FLOAT, details TEXT) AS $$
DECLARE
    v_current_score FLOAT;
    v_baseline_score FLOAT;
    v_delta FLOAT;
BEGIN
    SELECT overall_score INTO v_current_score FROM eval_scorecards WHERE eval_run_id = p_eval_run_id;
    SELECT overall_score INTO v_baseline_score FROM eval_scorecards WHERE eval_run_id = p_baseline_run_id;

    v_delta := COALESCE(v_current_score, 0) - COALESCE(v_baseline_score, 0);

    RETURN QUERY SELECT
        v_delta < (-p_regression_threshold),
        v_delta,
        'Current: ' || ROUND(COALESCE(v_current_score, 0)::NUMERIC, 3)::TEXT ||
        ', Baseline: ' || ROUND(COALESCE(v_baseline_score, 0)::NUMERIC, 3)::TEXT ||
        ', Delta: ' || ROUND(v_delta::NUMERIC, 3)::TEXT;
END;
$$ LANGUAGE plpgsql;


-- Immutable: eval results
CREATE TRIGGER eval_results_immutable_after_created
    BEFORE UPDATE ON eval_results
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('eval_results');
