-- Migration 025: Goal Management Infrastructure
--
-- Autonomy goals with lifecycle, evidence, budgets, conflicts, and reviews.
-- Goals are proposed by agents but controlled by governance rules.

-- Goal statuses
DROP TYPE IF EXISTS goal_status CASCADE;
CREATE TYPE goal_status AS ENUM (
    'proposed',
    'under_review',
    'approved',
    'rejected',
    'active',
    'blocked',
    'paused',
    'completed',
    'retired'
);

-- Autonomy levels
DROP TYPE IF EXISTS autonomy_level CASCADE;
CREATE TYPE autonomy_level AS ENUM (
    'L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6'
);

-- Risk levels (shared across goals, plans, outcomes)
DROP TYPE IF EXISTS risk_level CASCADE;
CREATE TYPE risk_level AS ENUM (
    'critical',
    'high',
    'medium',
    'low'
);

-- Main goals table
CREATE TABLE IF NOT EXISTS autonomy_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    source TEXT NOT NULL CHECK (source IN ('agent_proposed', 'perception_derived', 'governance_mandated', 'manual')),
    proposed_by TEXT NOT NULL,
    owning_agent_id UUID,
    owning_institution_id UUID,
    domain TEXT NOT NULL,
    expected_value NUMERIC(10, 2),
    risk_level risk_level NOT NULL DEFAULT 'medium',
    autonomy_level_allowed autonomy_level NOT NULL DEFAULT 'L2',
    status goal_status NOT NULL DEFAULT 'proposed',
    parent_goal_id UUID REFERENCES autonomy_goals(id),
    success_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    stop_conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id TEXT,
    run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_autonomy_goals_status ON autonomy_goals(status);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_owning_agent ON autonomy_goals(owning_agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_owning_institution ON autonomy_goals(owning_institution_id);

-- Add columns expected by downstream migrations
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS simulation_derived BOOLEAN DEFAULT false;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_domain ON autonomy_goals(domain);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_risk_level ON autonomy_goals(risk_level);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_parent ON autonomy_goals(parent_goal_id);


-- Goal evidence
CREATE TABLE IF NOT EXISTS goal_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    evidence_type TEXT NOT NULL CHECK (evidence_type IN (
        'perception_artifact',
        'historical_outcome',
        'simulation_result',
        'policy_requirement',
        'governance_mandate',
        'custom'
    )),
    evidence_ref TEXT NOT NULL,
    evidence_hash TEXT,
    relevance_score FLOAT NOT NULL CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_evidence_goal_id ON goal_evidence(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_evidence_type ON goal_evidence(evidence_type);


-- Goal conflicts
CREATE TABLE IF NOT EXISTS goal_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflicting_goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflict_type TEXT NOT NULL CHECK (conflict_type IN (
        'resource_contention',
        'mutual_exclusion',
        'precedence_violation',
        'policy_conflict',
        'institutional_conflict',
        'custom'
    )),
    severity risk_level NOT NULL DEFAULT 'medium',
    resolution_status TEXT CHECK (resolution_status IN ('unresolved', 'sequenced', 'merged', 'one_blocked')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_conflicts_goal_id ON goal_conflicts(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_conflicts_conflicting_goal_id ON goal_conflicts(conflicting_goal_id);


-- Goal budgets
CREATE TABLE IF NOT EXISTS goal_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL UNIQUE REFERENCES autonomy_goals(id),
    compute_budget BIGINT,
    token_budget BIGINT,
    time_budget_seconds BIGINT,
    tool_budget_json JSONB DEFAULT '{}'::jsonb,
    spend_limit NUMERIC(12, 2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_budgets_goal_id ON goal_budgets(goal_id);


-- Goal reviews
CREATE TABLE IF NOT EXISTS goal_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    reviewer_id TEXT NOT NULL,
    reviewer_role TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'conditional', 'deferred')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_reviews_goal_id ON goal_reviews(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_reviews_reviewer_id ON goal_reviews(reviewer_id);


-- Goal status events (audit trail)
CREATE TABLE IF NOT EXISTS goal_status_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    previous_status goal_status,
    new_status goal_status NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('agent', 'service', 'governor', 'system')),
    actor_id TEXT,
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_status_events_goal_id ON goal_status_events(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_status_events_new_status ON goal_status_events(new_status);
CREATE INDEX IF NOT EXISTS idx_goal_status_events_created_at ON goal_status_events(created_at);


-- Immutable: goal evidence and audit trail
DROP TRIGGER IF EXISTS goal_evidence_immutable ON goal_evidence;
CREATE TRIGGER goal_evidence_immutable
    BEFORE UPDATE ON goal_evidence
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('goal_evidence');

DROP TRIGGER IF EXISTS goal_status_events_immutable ON goal_status_events;
CREATE TRIGGER goal_status_events_immutable
    BEFORE UPDATE ON goal_status_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('goal_status_events');

-- Prevent deletion of completed goals
DROP TRIGGER IF EXISTS goal_prevent_deletion ON autonomy_goals;
CREATE TRIGGER goal_prevent_deletion
    BEFORE DELETE ON autonomy_goals
    FOR EACH ROW
    WHEN (OLD.status IN ('completed', 'retired'))
    EXECUTE FUNCTION raise_immutability_violation('autonomy_goals (completed/retired cannot delete)');
