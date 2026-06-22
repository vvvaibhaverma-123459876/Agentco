-- Migration 025: Autonomy goal management
--
-- Goals track what agents are trying to accomplish. Prevents unconstrained
-- self-generated goals. All goals must have risk assessment and approval.

CREATE TABLE IF NOT EXISTS autonomy_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('system', 'agent', 'user', 'learner')),
    source_id TEXT,
    proposed_by TEXT NOT NULL,
    owning_agent_id TEXT,
    owning_institution_id TEXT,
    domain TEXT NOT NULL,
    expected_value FLOAT CHECK (expected_value >= 0.0 AND expected_value <= 100.0),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    autonomy_level_allowed INT NOT NULL DEFAULT 0 CHECK (autonomy_level_allowed >= 0 AND autonomy_level_allowed <= 6),
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN (
        'proposed',
        'under_review',
        'approved',
        'active',
        'paused',
        'completed',
        'rejected',
        'retired'
    )),
    parent_goal_id UUID REFERENCES autonomy_goals(id),
    success_criteria_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    stop_conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_autonomy_goals_status ON autonomy_goals(status);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_agent_id ON autonomy_goals(owning_agent_id);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_domain ON autonomy_goals(domain);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_risk_level ON autonomy_goals(risk_level);
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_created_at ON autonomy_goals(created_at);


-- Evidence supporting goal
CREATE TABLE IF NOT EXISTS goal_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    evidence_type TEXT NOT NULL CHECK (evidence_type IN (
        'user_request',
        'system_metric',
        'agent_proposal',
        'market_signal',
        'risk_assessment',
        'opportunity',
        'mitigation'
    )),
    evidence_ref TEXT NOT NULL,
    evidence_hash TEXT,
    relevance_score FLOAT NOT NULL CHECK (relevance_score >= 0.0 AND relevance_score <= 1.0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_evidence_goal_id ON goal_evidence(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_evidence_evidence_type ON goal_evidence(evidence_type);


-- Goal conflicts
CREATE TABLE IF NOT EXISTS goal_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflicting_goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    conflict_type TEXT NOT NULL CHECK (conflict_type IN (
        'resource_contention',
        'objective_contradiction',
        'time_constraint',
        'priority_inversion',
        'scope_overlap'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolution_status TEXT NOT NULL DEFAULT 'unresolved' CHECK (resolution_status IN (
        'unresolved',
        'acknowledged',
        'mitigated',
        'resolved'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(goal_id, conflicting_goal_id)
);

CREATE INDEX IF NOT EXISTS idx_goal_conflicts_goal_id ON goal_conflicts(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_conflicts_severity ON goal_conflicts(severity);


-- Budget limits on goals
CREATE TABLE IF NOT EXISTS goal_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id) UNIQUE,
    compute_budget_tokens INT,
    token_budget INT,
    time_budget_seconds INT,
    tool_budget_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    spend_limit_usd FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_budgets_goal_id ON goal_budgets(goal_id);


-- Goal reviews and approvals
CREATE TABLE IF NOT EXISTS goal_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID NOT NULL REFERENCES autonomy_goals(id),
    reviewer_id TEXT NOT NULL,
    review_type TEXT NOT NULL CHECK (review_type IN (
        'domain_feasibility',
        'risk_assessment',
        'resource_availability',
        'safety_check',
        'governance_approval'
    )),
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'needs_revision', 'deferred')),
    reason TEXT NOT NULL,
    recommendations TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_goal_reviews_goal_id ON goal_reviews(goal_id);
CREATE INDEX IF NOT EXISTS idx_goal_reviews_reviewer_id ON goal_reviews(reviewer_id);
CREATE INDEX IF NOT EXISTS idx_goal_reviews_decision ON goal_reviews(decision);
