-- Migration 027: Phases 9-13 Integrated Self-Improvement Loop
-- Learner/Replay → Simulation → Self-Modification → Artifact Registry → Canary/Rollback
--
-- This migration establishes the complete self-improvement control loop:
-- trajectory_store → replay_batch → learner_run → candidate →
-- simulator_validation → protected_surface_scan → eval → artifact_registry →
-- canary_plan → rollback_events

-- ============================================================
-- PHASE 9: LEARNER, REPLAY, AND OFFLINE TRAINING LOOP
-- ============================================================

CREATE TYPE learner_type AS ENUM (
    'planner_heuristic',
    'memory_retrieval_policy',
    'escalation_threshold',
    'prompt_config',
    'tool_selection_policy',
    'model_routing_policy'
);

CREATE TYPE candidate_type AS ENUM (
    'planner_heuristic',
    'memory_policy',
    'escalation_config',
    'prompt_template',
    'tool_policy',
    'model_config',
    'code_patch'
);

CREATE TYPE learner_status AS ENUM (
    'initialized',
    'running',
    'completed',
    'failed'
);

-- Replay batches (trajectory groupings for training)
CREATE TABLE IF NOT EXISTS replay_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filter_json JSONB,
    trajectory_ids UUID[] NOT NULL,
    batch_hash TEXT NOT NULL UNIQUE,
    batch_label TEXT,
    simulation_derived BOOLEAN DEFAULT false,
    created_by TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_replay_batches_hash ON replay_batches(batch_hash);
CREATE INDEX idx_replay_batches_simulation ON replay_batches(simulation_derived);

-- Learner runs (training jobs)
CREATE TABLE IF NOT EXISTS learner_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_type learner_type NOT NULL,
    input_replay_batch_id UUID NOT NULL REFERENCES replay_batches(id),
    baseline_policy_version TEXT,
    candidate_policy_version TEXT,
    status learner_status NOT NULL DEFAULT 'initialized',
    metrics_json JSONB DEFAULT '{}'::jsonb,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_learner_runs_status ON learner_runs(status);
CREATE INDEX idx_learner_runs_batch_id ON learner_runs(input_replay_batch_id);
CREATE INDEX idx_learner_runs_learner_type ON learner_runs(learner_type);

-- Policy versions (versioned improvement artifacts)
CREATE TABLE IF NOT EXISTS policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type TEXT NOT NULL,
    name TEXT NOT NULL,
    version INT NOT NULL,
    artifact_hash TEXT NOT NULL,
    config_json JSONB,
    prompt_ref TEXT,
    model_ref TEXT,
    parent_policy_version_id UUID REFERENCES policy_versions(id),
    simulation_trained BOOLEAN DEFAULT false,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(policy_type, name, version)
);

CREATE INDEX idx_policy_versions_name_version ON policy_versions(name, version);
CREATE INDEX idx_policy_versions_simulation ON policy_versions(simulation_trained);

-- Learner candidates (proposed improvements)
CREATE TABLE IF NOT EXISTS learner_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_run_id UUID NOT NULL REFERENCES learner_runs(id),
    candidate_type candidate_type NOT NULL,
    artifact_ref TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    rationale TEXT,
    expected_improvement_json JSONB DEFAULT '{}'::jsonb,
    risk_level TEXT,
    simulation_trained BOOLEAN DEFAULT false,
    status TEXT NOT NULL DEFAULT 'generated',
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_learner_candidates_run_id ON learner_candidates(learner_run_id);
CREATE INDEX idx_learner_candidates_status ON learner_candidates(status);
CREATE INDEX idx_learner_candidates_type ON learner_candidates(candidate_type);

-- Replay training metrics (per-batch training results)
CREATE TABLE IF NOT EXISTS replay_training_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_run_id UUID NOT NULL REFERENCES learner_runs(id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT,
    dataset_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_replay_training_metrics_learner_run ON replay_training_metrics(learner_run_id);

-- ============================================================
-- PHASE 10: CONTROLLED SIMULATION ENVIRONMENTS
-- ============================================================

-- Simulator configurations
CREATE TABLE IF NOT EXISTS simulator_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_name TEXT NOT NULL,
    config_json JSONB NOT NULL,
    seed INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_simulator_configs_name ON simulator_configs(simulator_name);

-- Simulator runs
CREATE TABLE IF NOT EXISTS simulator_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_name TEXT NOT NULL,
    config_id UUID REFERENCES simulator_configs(id),
    seed INT,
    status TEXT NOT NULL DEFAULT 'initialized',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_simulator_runs_name ON simulator_runs(simulator_name);
CREATE INDEX idx_simulator_runs_status ON simulator_runs(status);

-- Simulator steps (episode observations)
CREATE TABLE IF NOT EXISTS simulator_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_run_id UUID NOT NULL REFERENCES simulator_runs(id),
    step_index INT NOT NULL,
    observation_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    reward FLOAT,
    done BOOLEAN,
    info_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_simulator_steps_run_id ON simulator_steps(simulator_run_id);

-- Simulator outcomes
CREATE TABLE IF NOT EXISTS simulator_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_run_id UUID NOT NULL REFERENCES simulator_runs(id),
    outcome_json JSONB,
    total_reward FLOAT,
    success BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_simulator_outcomes_run_id ON simulator_outcomes(simulator_run_id);

-- ============================================================
-- PHASE 11: SELF-MODIFICATION PIPELINE
-- ============================================================

CREATE TYPE self_modification_status AS ENUM (
    'requested',
    'generating',
    'scanning',
    'validating',
    'testing',
    'evaluating',
    'approved',
    'rejected',
    'blocked'
);

-- Self-modification requests
CREATE TABLE IF NOT EXISTS self_modification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    goal_id UUID,
    task_id UUID,
    requested_change_type TEXT NOT NULL,
    target_component TEXT NOT NULL,
    risk_level TEXT,
    status self_modification_status NOT NULL DEFAULT 'requested',
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_self_modification_requests_status ON self_modification_requests(status);

-- Self-modification candidates
CREATE TABLE IF NOT EXISTS self_modification_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES self_modification_requests(id),
    artifact_type TEXT NOT NULL,
    artifact_ref TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    generated_by TEXT,
    rationale TEXT,
    diff_summary TEXT,
    protected_surface_check BOOLEAN,
    status TEXT NOT NULL DEFAULT 'generated',
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_self_modification_candidates_request_id ON self_modification_candidates(request_id);
CREATE INDEX idx_self_modification_candidates_status ON self_modification_candidates(status);

-- Self-modification validations
CREATE TABLE IF NOT EXISTS self_modification_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES self_modification_candidates(id),
    validation_type TEXT NOT NULL,
    status TEXT NOT NULL,
    logs_ref TEXT,
    metrics_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_self_modification_validations_candidate_id ON self_modification_validations(candidate_id);

-- Promotion decisions (approval/rejection after eval)
CREATE TABLE IF NOT EXISTS promotion_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES learner_candidates(id),
    decision TEXT NOT NULL,
    decided_by TEXT,
    reason TEXT,
    risk_level TEXT,
    eval_run_id UUID,
    canary_plan_id UUID,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_promotion_decisions_candidate_id ON promotion_decisions(candidate_id);
CREATE INDEX idx_promotion_decisions_decision ON promotion_decisions(decision);

-- ============================================================
-- PHASE 12: ARTIFACT REGISTRY
-- ============================================================

CREATE TYPE artifact_type AS ENUM (
    'prompt',
    'policy',
    'model_config',
    'planner_config',
    'memory_policy',
    'tool_policy',
    'code_patch',
    'eval_suite',
    'reward_function',
    'simulator_config'
);

-- Artifact registry (versioned, signed, immutable)
CREATE TABLE IF NOT EXISTS artifact_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_type artifact_type NOT NULL,
    name TEXT NOT NULL,
    version INT NOT NULL,
    hash TEXT NOT NULL,
    storage_uri TEXT,
    parent_artifact_id UUID REFERENCES artifact_registry(id),
    created_by TEXT,
    provenance_json JSONB DEFAULT '{}'::jsonb,
    simulation_trained BOOLEAN DEFAULT false,
    signature TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(artifact_type, name, version)
);

CREATE INDEX idx_artifact_registry_type_name ON artifact_registry(artifact_type, name);
CREATE INDEX idx_artifact_registry_hash ON artifact_registry(hash);

-- Artifact lineage (parent-child relationships)
CREATE TABLE IF NOT EXISTS artifact_lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    parent_artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    relation_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_artifact_lineage_artifact_id ON artifact_lineage(artifact_id);
CREATE INDEX idx_artifact_lineage_parent_id ON artifact_lineage(parent_artifact_id);

-- Artifact deployments
CREATE TABLE IF NOT EXISTS artifact_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    environment TEXT NOT NULL,
    deployment_status TEXT NOT NULL,
    canary_percentage INT,
    active BOOLEAN DEFAULT false,
    previous_artifact_id UUID REFERENCES artifact_registry(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_artifact_deployments_artifact_id ON artifact_deployments(artifact_id);
CREATE INDEX idx_artifact_deployments_environment ON artifact_deployments(environment);
CREATE INDEX idx_artifact_deployments_active ON artifact_deployments(active);

-- Artifact signatures
CREATE TABLE IF NOT EXISTS artifact_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    signer_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    public_key_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_artifact_signatures_artifact_id ON artifact_signatures(artifact_id);

-- ============================================================
-- PHASE 13: SAFE DEPLOYMENT, CANARY, AND ROLLBACK
-- ============================================================

-- Canary plans
CREATE TABLE IF NOT EXISTS canary_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    target_service TEXT NOT NULL,
    environment TEXT NOT NULL,
    initial_percentage INT,
    max_percentage INT,
    success_metrics_json JSONB DEFAULT '{}'::jsonb,
    failure_metrics_json JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'created',
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_canary_plans_artifact_id ON canary_plans(artifact_id);
CREATE INDEX idx_canary_plans_status ON canary_plans(status);

-- Canary observations (metric tracking)
CREATE TABLE IF NOT EXISTS canary_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id UUID NOT NULL REFERENCES canary_plans(id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT,
    threshold FLOAT,
    status TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_canary_observations_plan_id ON canary_observations(canary_plan_id);

-- Rollback events (immutable audit trail)
CREATE TABLE IF NOT EXISTS rollback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    previous_artifact_id UUID REFERENCES artifact_registry(id),
    deployment_id UUID REFERENCES artifact_deployments(id),
    reason TEXT NOT NULL,
    triggered_by TEXT,
    metrics_json JSONB DEFAULT '{}'::jsonb,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rollback_events_artifact_id ON rollback_events(artifact_id);
CREATE INDEX idx_rollback_events_deployment_id ON rollback_events(deployment_id);

-- Immutability triggers for critical tables
DROP TRIGGER IF EXISTS replay_training_metrics_immutable ON replay_training_metrics;
CREATE TRIGGER replay_training_metrics_immutable
    BEFORE UPDATE ON replay_training_metrics
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('replay_training_metrics');

DROP TRIGGER IF EXISTS simulator_steps_immutable ON simulator_steps;
CREATE TRIGGER simulator_steps_immutable
    BEFORE UPDATE ON simulator_steps
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('simulator_steps');

DROP TRIGGER IF EXISTS simulator_outcomes_immutable ON simulator_outcomes;
CREATE TRIGGER simulator_outcomes_immutable
    BEFORE UPDATE ON simulator_outcomes
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('simulator_outcomes');

DROP TRIGGER IF EXISTS self_modification_validations_immutable ON self_modification_validations;
CREATE TRIGGER self_modification_validations_immutable
    BEFORE UPDATE ON self_modification_validations
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('self_modification_validations');

DROP TRIGGER IF EXISTS promotion_decisions_immutable ON promotion_decisions;
CREATE TRIGGER promotion_decisions_immutable
    BEFORE UPDATE ON promotion_decisions
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('promotion_decisions');

DROP TRIGGER IF EXISTS artifact_registry_immutable ON artifact_registry;
CREATE TRIGGER artifact_registry_immutable
    BEFORE UPDATE ON artifact_registry
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('artifact_registry');

DROP TRIGGER IF EXISTS artifact_signatures_immutable ON artifact_signatures;
CREATE TRIGGER artifact_signatures_immutable
    BEFORE UPDATE ON artifact_signatures
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('artifact_signatures');

DROP TRIGGER IF EXISTS rollback_events_immutable ON rollback_events;
CREATE TRIGGER rollback_events_immutable
    BEFORE UPDATE ON rollback_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('rollback_events');

-- View for integrated improvement loop lineage
CREATE VIEW improvement_loop_lineage AS
    SELECT
        rb.id as replay_batch_id,
        lr.id as learner_run_id,
        lc.id as learner_candidate_id,
        ar.id as artifact_id,
        pd.decision as promotion_decision,
        cp.id as canary_plan_id,
        re.id as rollback_event_id,
        lr.trace_id
    FROM replay_batches rb
    LEFT JOIN learner_runs lr ON lr.input_replay_batch_id = rb.id
    LEFT JOIN learner_candidates lc ON lc.learner_run_id = lr.id
    LEFT JOIN artifact_registry ar ON ar.id = ANY(CAST(ARRAY[lc.id::text] AS UUID[]))
    LEFT JOIN promotion_decisions pd ON pd.candidate_id = lc.id
    LEFT JOIN canary_plans cp ON cp.artifact_id = ar.id
    LEFT JOIN rollback_events re ON re.artifact_id = ar.id;
