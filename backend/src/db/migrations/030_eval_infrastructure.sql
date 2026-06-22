-- Migration 030: Evaluation infrastructure
--
-- Evaluation suites, runs, and results tracking

CREATE TABLE IF NOT EXISTS eval_suites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    eval_type TEXT NOT NULL CHECK (eval_type IN (
        'safety',
        'performance',
        'consistency',
        'alignment',
        'regression',
        'custom'
    )),
    active BOOLEAN NOT NULL DEFAULT true,
    total_cases INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_suites_name ON eval_suites(name);
CREATE INDEX IF NOT EXISTS idx_eval_suites_eval_type ON eval_suites(eval_type);


CREATE TABLE IF NOT EXISTS eval_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_suite_id UUID REFERENCES eval_suites(id),
    artifact_id UUID,
    run_timestamp TIMESTAMPTZ NOT NULL,
    passed_cases INT NOT NULL DEFAULT 0,
    failed_cases INT NOT NULL DEFAULT 0,
    skipped_cases INT NOT NULL DEFAULT 0,
    total_duration_ms INT,
    status TEXT NOT NULL DEFAULT 'completed' CHECK (status IN ('running', 'completed', 'failed')),
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_runs_eval_suite_id ON eval_runs(eval_suite_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_artifact_id ON eval_runs(artifact_id);
CREATE INDEX IF NOT EXISTS idx_eval_runs_status ON eval_runs(status);


CREATE TABLE IF NOT EXISTS eval_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    eval_run_id UUID NOT NULL REFERENCES eval_runs(id),
    test_case_id TEXT NOT NULL,
    test_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    execution_time_ms INT,
    error_message TEXT,
    assertion_details_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_eval_results_eval_run_id ON eval_results(eval_run_id);
CREATE INDEX IF NOT EXISTS idx_eval_results_passed ON eval_results(passed);
