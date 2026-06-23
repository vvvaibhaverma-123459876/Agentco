-- Migration 028: Trust Policy Versions
--
-- Implements versioned, evaluated, signed trust policies that civilization can
-- propose and activate. Policies control calibration behavior without modifying
-- the constitution or protected surfaces.
--
-- Policy lifecycle: draft → under_review → eval_required → approved/failed → canary → active → rolled_back/retired

-- ============================================================
-- POLICY TYPE ENUM
-- ============================================================

DROP TYPE IF EXISTS policy_status CASCADE;
CREATE TYPE policy_status AS ENUM (
    'draft', 'under_review', 'eval_required', 'eval_failed', 'approved',
    'canary', 'active', 'rolled_back', 'retired'
);

DROP TYPE IF EXISTS policy_type CASCADE;
CREATE TYPE policy_type AS ENUM (
    'confidence_discount',
    'evidence_standard',
    'reputation_weight',
    'dispute_resolution',
    'simulation_discount',
    'trust_decay_rate',
    'promotion_threshold',
    'emergency_freeze',
    'escalation_threshold'
);

DROP TYPE IF EXISTS policy_promotion_scope CASCADE;
CREATE TYPE policy_promotion_scope AS ENUM (
    'agent', 'team', 'institution', 'society', 'civilization'
);

-- ============================================================
-- TRUST POLICY VERSIONS TABLE
-- ============================================================

DROP TABLE IF EXISTS trust_policy_versions CASCADE;
CREATE TABLE trust_policy_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_type policy_type NOT NULL,
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    title TEXT NOT NULL,
    description TEXT,
    version_number INT NOT NULL,
    content_json JSONB NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    signature VARCHAR(256),
    creator_entity_id UUID,
    parent_policy_id UUID REFERENCES trust_policy_versions(id),
    promotion_scope policy_promotion_scope NOT NULL DEFAULT 'civilization',
    status policy_status NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_for_review_at TIMESTAMPTZ,
    eval_required_at TIMESTAMPTZ,
    eval_completed_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    canary_started_at TIMESTAMPTZ,
    canary_ended_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    retired_at TIMESTAMPTZ,
    trace_id TEXT
);

CREATE INDEX idx_trust_policy_type ON trust_policy_versions(policy_type);
CREATE INDEX idx_trust_policy_status ON trust_policy_versions(status);
CREATE INDEX idx_trust_policy_scope ON trust_policy_versions(promotion_scope);
CREATE INDEX idx_trust_policy_constitution ON trust_policy_versions(constitution_id);
CREATE INDEX idx_trust_policy_parent ON trust_policy_versions(parent_policy_id);
CREATE INDEX idx_trust_policy_created_at ON trust_policy_versions(created_at);
CREATE INDEX idx_trust_policy_activated_at ON trust_policy_versions(activated_at);

-- ============================================================
-- ACTIVE TRUST POLICIES TABLE
-- ============================================================

DROP TABLE IF EXISTS active_trust_policies CASCADE;
CREATE TABLE active_trust_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    policy_type policy_type NOT NULL,
    promotion_scope policy_promotion_scope NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_active_trust_policies_type ON active_trust_policies(policy_type);
CREATE INDEX idx_active_trust_policies_scope ON active_trust_policies(promotion_scope);
CREATE INDEX idx_active_trust_policies_activated_at ON active_trust_policies(activated_at);

-- ============================================================
-- POLICY EVALUATIONS TABLE
-- ============================================================

DROP TABLE IF EXISTS policy_evaluations CASCADE;
CREATE TABLE policy_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    eval_suite_id UUID,
    eval_run_id UUID,
    passed BOOLEAN NOT NULL,
    calibration_regression FLOAT,
    confidence_shift FLOAT,
    false_positive_impact FLOAT,
    false_negative_impact FLOAT,
    reputation_impact FLOAT,
    dispute_impact FLOAT,
    simulation_leakage_risk FLOAT,
    safety_threshold_compliance FLOAT,
    rollback_feasibility FLOAT,
    audit_completeness FLOAT,
    recommendation TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_evaluations_policy ON policy_evaluations(policy_id);
CREATE INDEX idx_policy_evaluations_passed ON policy_evaluations(passed);

-- ============================================================
-- POLICY REVIEWS TABLE
-- ============================================================

DROP TABLE IF EXISTS policy_reviews CASCADE;
CREATE TABLE policy_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    reviewer_entity_id UUID,
    reviewer_role TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'conditional')),
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_reviews_policy ON policy_reviews(policy_id);
CREATE INDEX idx_policy_reviews_decision ON policy_reviews(decision);

-- ============================================================
-- POLICY CANARY DEPLOYMENTS TABLE
-- ============================================================

DROP TABLE IF EXISTS policy_canary_deployments CASCADE;
CREATE TABLE policy_canary_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    previous_policy_id UUID REFERENCES trust_policy_versions(id),
    canary_scope_json JSONB DEFAULT '{}'::jsonb,
    target_agents INT,
    target_percentage FLOAT,
    status TEXT NOT NULL DEFAULT 'starting',
    metrics_json JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    trace_id TEXT
);

CREATE INDEX idx_policy_canary_policy ON policy_canary_deployments(policy_id);
CREATE INDEX idx_policy_canary_status ON policy_canary_deployments(status);

-- ============================================================
-- POLICY CHANGE EVENTS (AUDIT TRAIL)
-- ============================================================

DROP TABLE IF EXISTS policy_change_events CASCADE;
CREATE TABLE policy_change_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    event_type TEXT NOT NULL,
    previous_status policy_status,
    new_status policy_status NOT NULL,
    actor_entity_id UUID,
    actor_role TEXT,
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_policy_change_events_policy ON policy_change_events(policy_id);
CREATE INDEX idx_policy_change_events_type ON policy_change_events(event_type);
CREATE INDEX idx_policy_change_events_status ON policy_change_events(new_status);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS trust_policy_versions_immutable ON trust_policy_versions;
CREATE TRIGGER trust_policy_versions_immutable
    BEFORE UPDATE ON trust_policy_versions
    FOR EACH ROW
    WHEN (OLD.status IN ('approved', 'active', 'rolled_back', 'retired'))
    EXECUTE FUNCTION raise_immutability_violation('trust_policy_versions in final state');

DROP TRIGGER IF EXISTS active_trust_policies_immutable ON active_trust_policies;
CREATE TRIGGER active_trust_policies_immutable
    BEFORE DELETE ON active_trust_policies
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('active_trust_policies history is immutable');

DROP TRIGGER IF EXISTS policy_evaluations_immutable ON policy_evaluations;
CREATE TRIGGER policy_evaluations_immutable
    BEFORE UPDATE ON policy_evaluations
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('policy_evaluations');

DROP TRIGGER IF EXISTS policy_reviews_immutable ON policy_reviews;
CREATE TRIGGER policy_reviews_immutable
    BEFORE UPDATE ON policy_reviews
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('policy_reviews');

DROP TRIGGER IF EXISTS policy_change_events_immutable ON policy_change_events;
CREATE TRIGGER policy_change_events_immutable
    BEFORE UPDATE ON policy_change_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('policy_change_events');

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION get_active_policy(p_policy_type policy_type, p_scope policy_promotion_scope)
RETURNS UUID AS $$
DECLARE
    v_policy_id UUID;
BEGIN
    SELECT policy_id INTO v_policy_id
    FROM active_trust_policies atp
    WHERE atp.policy_type = p_policy_type
    AND atp.promotion_scope = p_scope
    ORDER BY atp.activated_at DESC
    LIMIT 1;

    RETURN v_policy_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_policy_by_id(p_policy_id UUID)
RETURNS TABLE (
    id UUID, policy_type policy_type, title TEXT, status policy_status,
    version_number INT, created_at TIMESTAMPTZ, activated_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT tpv.id, tpv.policy_type, tpv.title, tpv.status,
           tpv.version_number, tpv.created_at, tpv.activated_at
    FROM trust_policy_versions tpv
    WHERE tpv.id = p_policy_id;
END;
$$ LANGUAGE plpgsql;
