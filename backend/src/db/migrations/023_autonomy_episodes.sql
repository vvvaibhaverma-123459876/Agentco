-- Migration 023: Autonomy episodes and trajectory infrastructure
--
-- Stores complete episodes (task execution traces) with actions, outcomes,
-- and interventions. Foundation for memory kernel and learner.

CREATE TABLE IF NOT EXISTS autonomy_episodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES autonomy_tasks(id),
    run_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    institution_id TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    domain TEXT,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    autonomy_level INT NOT NULL DEFAULT 0 CHECK (autonomy_level >= 0 AND autonomy_level <= 6),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    outcome_status TEXT CHECK (outcome_status IN ('success', 'partial_success', 'failure', 'cancelled')),
    reward_score FLOAT,
    regret_score FLOAT,
    intervention_required BOOLEAN NOT NULL DEFAULT false,
    intervention_count INT NOT NULL DEFAULT 0,
    human_override_count INT NOT NULL DEFAULT 0,
    trace_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_task_id ON autonomy_episodes(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_agent_id ON autonomy_episodes(agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_run_id ON autonomy_episodes(run_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_created_at ON autonomy_episodes(created_at);
CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_outcome_status ON autonomy_episodes(outcome_status);
CREATE INDEX IF NOT EXISTS idx_autonomy_episodes_regret_score ON autonomy_episodes(regret_score);


-- Individual actions within an episode
CREATE TABLE IF NOT EXISTS autonomy_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES autonomy_episodes(id),
    step_index INT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN (
        'tool_call',
        'goal_selection',
        'memory_read',
        'memory_write',
        'decision',
        'escalation',
        'recovery',
        'compensation'
    )),
    tool_name TEXT,
    input_hash TEXT,
    output_hash TEXT,
    confidence_reported FLOAT CHECK (confidence_reported >= 0.0 AND confidence_reported <= 1.0),
    confidence_trusted FLOAT CHECK (confidence_trusted >= 0.0 AND confidence_trusted <= 1.0),
    policy_version TEXT,
    prompt_version TEXT,
    model_version TEXT,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE(episode_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_autonomy_actions_episode_id ON autonomy_actions(episode_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_actions_action_type ON autonomy_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_actions_created_at ON autonomy_actions(created_at);


-- Outcomes of episodes
CREATE TABLE IF NOT EXISTS autonomy_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES autonomy_episodes(id),
    task_id UUID REFERENCES autonomy_tasks(id),
    outcome_type TEXT NOT NULL CHECK (outcome_type IN (
        'task_completion',
        'goal_achievement',
        'partial_completion',
        'failure',
        'user_cancelled',
        'system_cancelled',
        'escalated'
    )),
    outcome_status TEXT NOT NULL CHECK (outcome_status IN ('success', 'partial_success', 'failure')),
    objective_result_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    evidence_refs_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_episode_id ON autonomy_outcomes(episode_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_task_id ON autonomy_outcomes(task_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_outcome_type ON autonomy_outcomes(outcome_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_outcomes_created_at ON autonomy_outcomes(created_at);


-- Human and system interventions during episodes
CREATE TABLE IF NOT EXISTS autonomy_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES autonomy_episodes(id),
    intervention_type TEXT NOT NULL CHECK (intervention_type IN (
        'human_override',
        'policy_enforcement',
        'safety_block',
        'resource_limit',
        'timeout',
        'escalation',
        'rollback_trigger'
    )),
    intervention_actor TEXT NOT NULL CHECK (intervention_actor IN (
        'human',
        'system',
        'policy_engine',
        'safety_monitor',
        'resource_manager'
    )),
    reason TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'error', 'critical')),
    before_state_json JSONB,
    after_state_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomy_interventions_episode_id ON autonomy_interventions(episode_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_interventions_intervention_type ON autonomy_interventions(intervention_type);
CREATE INDEX IF NOT EXISTS idx_autonomy_interventions_severity ON autonomy_interventions(severity);
CREATE INDEX IF NOT EXISTS idx_autonomy_interventions_created_at ON autonomy_interventions(created_at);


-- Memory retrieval events for quality tracking
CREATE TABLE IF NOT EXISTS memory_retrieval_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash TEXT NOT NULL,
    retrieved_episode_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    retrieval_strategy TEXT NOT NULL CHECK (retrieval_strategy IN (
        'semantic_similarity',
        'temporal_recency',
        'relevance_scoring',
        'regret_aware',
        'contradiction_aware',
        'hybrid'
    )),
    relevance_scores_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    used_in_task_id UUID REFERENCES autonomy_tasks(id),
    feedback_score FLOAT CHECK (feedback_score >= 0.0 AND feedback_score <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_retrieval_events_query_hash ON memory_retrieval_events(query_hash);
CREATE INDEX IF NOT EXISTS idx_memory_retrieval_events_used_in_task ON memory_retrieval_events(used_in_task_id);
CREATE INDEX IF NOT EXISTS idx_memory_retrieval_events_created_at ON memory_retrieval_events(created_at);


-- Trajectory store: full environment transitions for replay
CREATE TABLE IF NOT EXISTS trajectory_store (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id UUID NOT NULL REFERENCES autonomy_episodes(id),
    task_id UUID REFERENCES autonomy_tasks(id),
    step_index INT NOT NULL,
    state_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    observation_json JSONB NOT NULL,
    reward FLOAT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT false,
    info_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    policy_version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(episode_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_trajectory_store_episode_id ON trajectory_store(episode_id);
CREATE INDEX IF NOT EXISTS idx_trajectory_store_task_id ON trajectory_store(task_id);
CREATE INDEX IF NOT EXISTS idx_trajectory_store_created_at ON trajectory_store(created_at);


-- Replay batches for training
CREATE TABLE IF NOT EXISTS replay_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_filter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trajectory_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    batch_hash TEXT NOT NULL UNIQUE,
    batch_size INT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_replay_batches_batch_hash ON replay_batches(batch_hash);
CREATE INDEX IF NOT EXISTS idx_replay_batches_created_at ON replay_batches(created_at);


-- Immutable: episodes cannot be modified after creation
CREATE TRIGGER autonomy_episodes_immutable_after_created
    BEFORE UPDATE ON autonomy_episodes
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('autonomy_episodes');

CREATE TRIGGER autonomy_actions_immutable_after_created
    BEFORE UPDATE ON autonomy_actions
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('autonomy_actions');

CREATE TRIGGER autonomy_outcomes_immutable_after_created
    BEFORE UPDATE ON autonomy_outcomes
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('autonomy_outcomes');

CREATE TRIGGER trajectory_store_immutable_after_created
    BEFORE UPDATE ON trajectory_store
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('trajectory_store');
