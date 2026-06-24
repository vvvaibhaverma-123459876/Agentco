-- Migration 034: Policy control plane
--
-- Governance rules, policy evaluation, risk assessment, and emergency
-- controls. Kill switch always available.

CREATE TABLE IF NOT EXISTS policy_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    rule_type TEXT NOT NULL CHECK (rule_type IN (
        'prohibition',
        'requirement',
        'preference',
        'escalation',
        'emergency'
    )),
    severity TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'error', 'critical')),
    expression_json JSONB NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_policy_rules_domain ON policy_rules(domain);
CREATE INDEX IF NOT EXISTS idx_policy_rules_active ON policy_rules(active);
CREATE INDEX IF NOT EXISTS idx_policy_rules_severity ON policy_rules(severity);


-- Policy evaluation results
CREATE TABLE IF NOT EXISTS policy_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES policy_rules(id),
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('pass', 'fail', 'warning')),
    reason TEXT,
    evaluation_details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_policy_evaluations_rule_id ON policy_evaluations(rule_id);
CREATE INDEX IF NOT EXISTS idx_policy_evaluations_subject_id ON policy_evaluations(subject_id);
CREATE INDEX IF NOT EXISTS idx_policy_evaluations_decision ON policy_evaluations(decision);
CREATE INDEX IF NOT EXISTS idx_policy_evaluations_created_at ON policy_evaluations(created_at);


-- Governance decisions
CREATE TABLE IF NOT EXISTS governance_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_type TEXT NOT NULL CHECK (decision_type IN (
        'goal_approval',
        'plan_approval',
        'policy_promotion',
        'authority_expansion',
        'risk_acceptance',
        'exception_grant',
        'emergency_control'
    )),
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    approved_by TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'pending', 'deferred')),
    reason TEXT NOT NULL,
    conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_governance_decisions_decision_type ON governance_decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_governance_decisions_decision ON governance_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_governance_decisions_created_at ON governance_decisions(created_at);


-- Risk assessments
CREATE TABLE IF NOT EXISTS risk_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_factors_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    mitigation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    assessed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_subject_id ON risk_assessments(subject_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_level ON risk_assessments(risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_created_at ON risk_assessments(created_at);


-- Emergency controls
CREATE TABLE IF NOT EXISTS emergency_controls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_name TEXT NOT NULL UNIQUE,
    control_type TEXT NOT NULL CHECK (control_type IN (
        'kill_switch',
        'autonomous_pause',
        'high_risk_freeze',
        'resource_limit',
        'network_isolation'
    )),
    status TEXT NOT NULL DEFAULT 'inactive' CHECK (status IN ('inactive', 'active', 'triggered', 'released')),
    activated_by TEXT,
    reason TEXT,
    activated_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    effects_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emergency_controls_status ON emergency_controls(status);
CREATE INDEX IF NOT EXISTS idx_emergency_controls_created_at ON emergency_controls(created_at);


-- Initialize critical emergency controls
INSERT INTO emergency_controls (control_name, control_type, reason) VALUES
('main_kill_switch', 'kill_switch', 'Main system shutdown'),
('autonomous_pause', 'autonomous_pause', 'Pause all autonomous execution'),
('high_risk_freeze', 'high_risk_freeze', 'Freeze high-risk goals/tasks'),
('network_isolation', 'network_isolation', 'Disable external network access')
ON CONFLICT DO NOTHING;


-- Helper: check if policy violations exist
CREATE OR REPLACE FUNCTION check_policy_violations(
    p_subject_type TEXT,
    p_subject_id TEXT
) RETURNS TABLE(has_violations BOOLEAN, violations TEXT[], severity TEXT) AS $$
DECLARE
    v_violations TEXT[] := ARRAY[]::TEXT[];
    v_severity TEXT := 'info';
BEGIN
    -- In production, evaluate all applicable policy rules
    -- For now, return structure
    RETURN QUERY SELECT
        false,
        v_violations,
        v_severity;
END;
$$ LANGUAGE plpgsql;


-- Helper: activate emergency control
CREATE OR REPLACE FUNCTION activate_emergency_control(
    p_control_name TEXT,
    p_activated_by TEXT,
    p_reason TEXT
) RETURNS VOID AS $$
BEGIN
    UPDATE emergency_controls
    SET status = 'active', activated_at = now(),
        activated_by = p_activated_by, reason = p_reason
    WHERE control_name = p_control_name;
END;
$$ LANGUAGE plpgsql;


-- Helper: release emergency control
CREATE OR REPLACE FUNCTION release_emergency_control(
    p_control_name TEXT
) RETURNS VOID AS $$
BEGIN
    UPDATE emergency_controls
    SET status = 'released', released_at = now()
    WHERE control_name = p_control_name;
END;
$$ LANGUAGE plpgsql;
