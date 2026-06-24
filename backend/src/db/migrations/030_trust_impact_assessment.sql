-- Migration 030: Trust Impact Assessment
--
-- Implements impact assessment for proposed changes before allowing canary deployment.
-- Assesses impact across 10 metrics and produces recommendation.

-- ============================================================
-- IMPACT ASSESSMENT TABLES
-- ============================================================

DROP TABLE IF EXISTS trust_impact_assessments CASCADE;
CREATE TABLE trust_impact_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_request_id UUID REFERENCES calibration_change_requests(id),
    policy_id UUID REFERENCES trust_policy_versions(id),
    assessment_type TEXT NOT NULL,
    baseline_policy_id UUID REFERENCES trust_policy_versions(id),
    calibration_regression FLOAT NOT NULL DEFAULT 0.0,
    confidence_shift FLOAT NOT NULL DEFAULT 0.0,
    false_positive_impact FLOAT NOT NULL DEFAULT 0.0,
    false_negative_impact FLOAT NOT NULL DEFAULT 0.0,
    reputation_impact FLOAT NOT NULL DEFAULT 0.0,
    dispute_impact FLOAT NOT NULL DEFAULT 0.0,
    simulation_leakage_risk FLOAT NOT NULL DEFAULT 0.0,
    safety_threshold_compliance FLOAT NOT NULL DEFAULT 0.0,
    rollback_feasibility FLOAT NOT NULL DEFAULT 0.0,
    audit_completeness FLOAT NOT NULL DEFAULT 0.0,
    recommendation TEXT NOT NULL,
    recommendation_confidence FLOAT NOT NULL,
    supporting_evidence_json JSONB DEFAULT '{}'::jsonb,
    blocking_issues TEXT[],
    warnings TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_impact_assessments_change ON trust_impact_assessments(change_request_id);
CREATE INDEX idx_impact_assessments_policy ON trust_impact_assessments(policy_id);
CREATE INDEX idx_impact_assessments_baseline ON trust_impact_assessments(baseline_policy_id);
CREATE INDEX idx_impact_assessments_recommendation ON trust_impact_assessments(recommendation);

-- ============================================================
-- BASELINE METRICS TABLE
-- ============================================================

DROP TABLE IF EXISTS baseline_metrics CASCADE;
CREATE TABLE baseline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID NOT NULL REFERENCES trust_policy_versions(id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    measurement_timestamp TIMESTAMPTZ NOT NULL,
    context_json JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_baseline_metrics_policy ON baseline_metrics(policy_id);
CREATE INDEX idx_baseline_metrics_name ON baseline_metrics(metric_name);
CREATE INDEX idx_baseline_metrics_timestamp ON baseline_metrics(measurement_timestamp DESC);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS impact_assessments_immutable ON trust_impact_assessments;
CREATE TRIGGER impact_assessments_immutable
    BEFORE UPDATE ON trust_impact_assessments
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('trust_impact_assessments');

DROP TRIGGER IF EXISTS baseline_metrics_immutable ON baseline_metrics;
CREATE TRIGGER baseline_metrics_immutable
    BEFORE UPDATE ON baseline_metrics
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('baseline_metrics');

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION get_baseline_metrics_for_policy(p_policy_id UUID)
RETURNS TABLE (
    metric_name TEXT, metric_value FLOAT, measurement_timestamp TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT bm.metric_name, bm.metric_value, bm.measurement_timestamp
    FROM baseline_metrics bm
    WHERE bm.policy_id = p_policy_id
    ORDER BY bm.measurement_timestamp DESC;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION assess_recommendation(
    p_calibration_regression FLOAT,
    p_confidence_shift FLOAT,
    p_false_positive_impact FLOAT,
    p_false_negative_impact FLOAT,
    p_reputation_impact FLOAT,
    p_dispute_impact FLOAT,
    p_simulation_leakage_risk FLOAT,
    p_safety_threshold_compliance FLOAT,
    p_rollback_feasibility FLOAT,
    p_audit_completeness FLOAT
)
RETURNS TEXT AS $$
DECLARE
    v_score FLOAT;
    v_blocking_count INT := 0;
BEGIN
    -- Calculate composite score
    v_score := (
        (1.0 - ABS(p_calibration_regression)) * 0.20 +
        (1.0 - ABS(p_confidence_shift)) * 0.15 +
        (1.0 - p_false_positive_impact) * 0.10 +
        (1.0 - p_false_negative_impact) * 0.10 +
        (1.0 - ABS(p_reputation_impact)) * 0.10 +
        (1.0 - ABS(p_dispute_impact)) * 0.10 +
        (1.0 - p_simulation_leakage_risk) * 0.05 +
        p_safety_threshold_compliance * 0.10 +
        p_rollback_feasibility * 0.05 +
        p_audit_completeness * 0.05
    );

    -- Detect blocking issues
    IF p_calibration_regression > 0.05 THEN
        v_blocking_count := v_blocking_count + 1;
    END IF;

    IF p_safety_threshold_compliance < 0.95 THEN
        v_blocking_count := v_blocking_count + 1;
    END IF;

    IF p_rollback_feasibility < 0.80 THEN
        v_blocking_count := v_blocking_count + 1;
    END IF;

    IF p_simulation_leakage_risk > 0.10 THEN
        v_blocking_count := v_blocking_count + 1;
    END IF;

    -- Produce recommendation based on score and blocking issues
    IF v_blocking_count > 0 THEN
        RETURN 'block';
    ELSIF v_score < 0.70 THEN
        RETURN 'require_human_review';
    ELSIF v_score < 0.85 THEN
        RETURN 'require_revision';
    ELSIF p_simulation_leakage_risk > 0.05 THEN
        RETURN 'sandbox_only';
    ELSE
        RETURN 'approve_for_canary';
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_safety_score(p_safety_threshold_compliance FLOAT)
RETURNS FLOAT AS $$
BEGIN
    RETURN p_safety_threshold_compliance;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_rollback_feasibility_score(p_rollback_feasibility FLOAT)
RETURNS FLOAT AS $$
BEGIN
    RETURN p_rollback_feasibility;
END;
$$ LANGUAGE plpgsql;
