-- Migration 020: Evaluation manifests and trial storage
--
-- Adds support for reproducible evaluation runs and trial records.
-- Includes benchmark specifications, eval runs, and trial data with
-- uncertainty and provenance tracking.

CREATE TABLE IF NOT EXISTS benchmark_manifests (
    benchmark_id        TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    description         TEXT NOT NULL,
    task_type           TEXT NOT NULL CHECK (task_type IN ('binary_classification', 'multiple_choice', 'free_form', 'agent_task')),
    dataset_uri         TEXT NOT NULL,
    dataset_hash        TEXT NOT NULL,  -- SHA256 hex, 64 chars
    dataset_version     TEXT NOT NULL,
    split               TEXT NOT NULL CHECK (split IN ('train', 'val', 'test')),
    scorer_ids          JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Array of scorer IDs
    license             TEXT NOT NULL,
    manifest_hash       TEXT NOT NULL,  -- SHA256 of manifest for reproducibility
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_benchmark_created_at ON benchmark_manifests(created_at);
CREATE INDEX idx_benchmark_dataset_hash ON benchmark_manifests(dataset_hash);

-- Immutable: no deletes/updates
CREATE TRIGGER benchmark_manifests_immutable
    BEFORE UPDATE OR DELETE ON benchmark_manifests
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('benchmark_manifests');


CREATE TABLE IF NOT EXISTS eval_runs (
    run_id              TEXT PRIMARY KEY,
    benchmark_id        TEXT NOT NULL REFERENCES benchmark_manifests(benchmark_id),
    commit_sha          TEXT NOT NULL,  -- Git commit SHA
    model_provider      TEXT NOT NULL,
    model_name          TEXT NOT NULL,
    agent_id            TEXT,
    agent_version       TEXT,
    prompt_version      TEXT NOT NULL,
    tool_profile        TEXT NOT NULL,  -- 'full', 'read-only', 'none', etc.
    temperature         FLOAT NOT NULL CHECK (temperature >= 0.0 AND temperature <= 2.0),
    top_p               FLOAT NOT NULL CHECK (top_p >= 0.0 AND top_p <= 1.0),
    max_tokens          INT NOT NULL CHECK (max_tokens >= 1),
    seed                INT,
    started_at          TIMESTAMPTZ NOT NULL,
    completed_at        TIMESTAMPTZ,
    status              TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_eval_runs_benchmark_id ON eval_runs(benchmark_id);
CREATE INDEX idx_eval_runs_model_name ON eval_runs(model_name);
CREATE INDEX idx_eval_runs_agent_id ON eval_runs(agent_id);
CREATE INDEX idx_eval_runs_status ON eval_runs(status);
CREATE INDEX idx_eval_runs_created_at ON eval_runs(created_at);


CREATE TABLE IF NOT EXISTS trial_records (
    trial_id            TEXT PRIMARY KEY,
    run_id              TEXT NOT NULL REFERENCES eval_runs(run_id),
    benchmark_id        TEXT NOT NULL REFERENCES benchmark_manifests(benchmark_id),
    task_id             TEXT NOT NULL,
    input_payload       JSONB NOT NULL,
    raw_output          TEXT NOT NULL,
    parsed_output       JSONB,
    expected_output     JSONB NOT NULL,
    trace               JSONB,
    tool_calls          JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Array of tool calls
    uncertainty         JSONB,  -- UncertaintySignal as JSON
    grading_result      JSONB NOT NULL,
    provenance          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trial_records_run_id ON trial_records(run_id);
CREATE INDEX idx_trial_records_benchmark_id ON trial_records(benchmark_id);
CREATE INDEX idx_trial_records_created_at ON trial_records(created_at);
CREATE INDEX idx_trial_records_task_id ON trial_records(task_id, run_id);  -- Composite for query efficiency


CREATE TABLE IF NOT EXISTS grading_results (
    grading_id          SERIAL PRIMARY KEY,
    trial_id            TEXT NOT NULL REFERENCES trial_records(trial_id),
    correctness         BOOLEAN NOT NULL,
    score               FLOAT NOT NULL,
    hallucination_flag  BOOLEAN NOT NULL DEFAULT false,
    policy_violation_flag BOOLEAN NOT NULL DEFAULT false,
    tool_error_flag     BOOLEAN NOT NULL DEFAULT false,
    explanation         TEXT NOT NULL DEFAULT '',
    grader_version      TEXT NOT NULL DEFAULT '1.0',
    rubric_version      TEXT NOT NULL DEFAULT '1.0',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_grading_results_trial_id ON grading_results(trial_id);
CREATE INDEX idx_grading_results_correctness ON grading_results(correctness);


CREATE TABLE IF NOT EXISTS eval_artifacts (
    artifact_id         SERIAL PRIMARY KEY,
    run_id              TEXT NOT NULL REFERENCES eval_runs(run_id),
    artifact_type       TEXT NOT NULL,  -- 'report', 'log', 'trace', etc.
    artifact_path       TEXT NOT NULL,
    artifact_hash       TEXT,  -- SHA256 of artifact
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_eval_artifacts_run_id ON eval_artifacts(run_id);
CREATE INDEX idx_eval_artifacts_type ON eval_artifacts(artifact_type);


-- Immutability enforcement for trial records (audit trail)
CREATE TRIGGER trial_records_immutable_after_created
    BEFORE UPDATE ON trial_records
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('trial_records');
