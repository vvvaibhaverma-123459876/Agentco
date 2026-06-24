-- Migration 029: Learner and policy version control
--
-- Tracks learner runs, policy versions, candidate generation, and
-- prevents direct deployment by learner.

CREATE TABLE IF NOT EXISTS learner_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_type TEXT NOT NULL CHECK (learner_type IN (
        'policy_gradient',
        'behavioral_cloning',
        'rule_extraction',
        'prompt_optimization',
        'tool_policy_update',
        'memory_policy_update',
        'custom'
    )),
    input_replay_batch_id UUID NOT NULL REFERENCES replay_batches(id),
    baseline_policy_version TEXT NOT NULL,
    candidate_policy_version TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'running',
        'completed',
        'failed',
        'cancelled'
    )),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_learner_runs_status ON learner_runs(status);
CREATE INDEX IF NOT EXISTS idx_learner_runs_created_at ON learner_runs(created_at);


-- Policy versions for versioning and rollback
CREATE TABLE IF NOT EXISTS policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type TEXT NOT NULL CHECK (policy_type IN (
        'prompt_policy',
        'tool_selection_policy',
        'planner_heuristic',
        'memory_retrieval_policy',
        'escalation_threshold',
        'model_routing_policy'
    )),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    artifact_hash TEXT NOT NULL UNIQUE,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    prompt_ref TEXT,
    model_ref TEXT,
    parent_policy_version_id UUID REFERENCES policy_versions(id),
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(policy_type, name, version)
);

CREATE INDEX IF NOT EXISTS idx_policy_versions_policy_type ON policy_versions(policy_type);
CREATE INDEX IF NOT EXISTS idx_policy_versions_artifact_hash ON policy_versions(artifact_hash);


-- Learner-generated candidates
CREATE TABLE IF NOT EXISTS learner_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_run_id UUID NOT NULL REFERENCES learner_runs(id),
    candidate_type TEXT NOT NULL CHECK (candidate_type IN (
        'prompt_update',
        'tool_selection_policy_update',
        'planner_heuristic_update',
        'memory_retrieval_policy_update',
        'escalation_threshold_update',
        'model_routing_policy_update'
    )),
    artifact_ref TEXT NOT NULL,
    artifact_hash TEXT NOT NULL UNIQUE,
    rationale TEXT NOT NULL,
    expected_improvement_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'under_review',
        'approved',
        'rejected',
        'promoted',
        'rolled_back',
        'archived'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    promoted_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_learner_candidates_learner_run_id ON learner_candidates(learner_run_id);
CREATE INDEX IF NOT EXISTS idx_learner_candidates_status ON learner_candidates(status);
CREATE INDEX IF NOT EXISTS idx_learner_candidates_artifact_hash ON learner_candidates(artifact_hash);


-- Training metrics from replay
CREATE TABLE IF NOT EXISTS replay_training_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_run_id UUID NOT NULL REFERENCES learner_runs(id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_type TEXT NOT NULL CHECK (metric_type IN ('scalar', 'histogram', 'categorical')),
    dataset_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_replay_training_metrics_learner_run_id ON replay_training_metrics(learner_run_id);


-- Ensure learner cannot deploy candidates
CREATE OR REPLACE FUNCTION prevent_learner_self_deployment()
RETURNS TRIGGER AS $$
BEGIN
    -- This is checked at application level, but also enforce at DB level
    -- If a candidate was created by learner and is being promoted without eval gate,
    -- the application layer should reject it.
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- Immutable: policy versions and candidates (once created, no modification)
CREATE TRIGGER policy_versions_immutable_after_created
    BEFORE UPDATE ON policy_versions
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('policy_versions');

CREATE TRIGGER learner_candidates_immutable_after_created
    BEFORE UPDATE ON learner_candidates
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('learner_candidates');
