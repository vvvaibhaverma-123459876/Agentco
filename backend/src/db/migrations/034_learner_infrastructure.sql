-- Migration 028: Learner infrastructure
--
-- Learner runs, candidates, and feedback tracking

CREATE TABLE IF NOT EXISTS learner_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    replay_batch_id UUID NOT NULL REFERENCES replay_batches(id),
    policy_version_before TEXT NOT NULL,
    policy_version_after TEXT,
    baseline_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    best_candidate_id UUID,
    candidate_count INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_learner_runs_replay_batch_id ON learner_runs(replay_batch_id);
CREATE INDEX IF NOT EXISTS idx_learner_runs_status ON learner_runs(status);
CREATE INDEX IF NOT EXISTS idx_learner_runs_created_at ON learner_runs(created_at);


CREATE TABLE IF NOT EXISTS learner_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_run_id UUID NOT NULL REFERENCES learner_runs(id),
    candidate_type TEXT NOT NULL CHECK (candidate_type IN (
        'prompt_update',
        'config_update',
        'heuristic_update',
        'memory_policy_update'
    )),
    artifact_id UUID NOT NULL,
    artifact_hash TEXT NOT NULL,
    metrics_before_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    metrics_after_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    improvement_percent FLOAT NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created', 'evaluated', 'promoted', 'rejected', 'rolled_back')),
    eval_feedback_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evaluated_at TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_learner_candidates_learner_run_id ON learner_candidates(learner_run_id);
CREATE INDEX IF NOT EXISTS idx_learner_candidates_status ON learner_candidates(status);
CREATE INDEX IF NOT EXISTS idx_learner_candidates_artifact_id ON learner_candidates(artifact_id);
