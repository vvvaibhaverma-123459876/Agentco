-- Migration 030: Self-modification pipeline
--
-- Controls autonomous system improvements. Candidates must pass protected
-- surface scan, eval gate, and governance approval before promotion.

CREATE TABLE IF NOT EXISTS self_modification_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL CHECK (source IN ('learner', 'agent', 'system', 'governance')),
    source_id TEXT,
    goal_id UUID REFERENCES autonomy_goals(id),
    task_id UUID REFERENCES autonomy_tasks(id),
    requested_change_type TEXT NOT NULL CHECK (requested_change_type IN (
        'prompt_update',
        'policy_update',
        'config_update',
        'feature_addition',
        'bug_fix',
        'optimization'
    )),
    target_component TEXT NOT NULL,
    target_surface TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'in_progress',
        'completed',
        'rejected',
        'cancelled'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_self_modification_requests_status ON self_modification_requests(status);
CREATE INDEX IF NOT EXISTS idx_self_modification_requests_risk_level ON self_modification_requests(risk_level);


-- Candidate artifact for modification
CREATE TABLE IF NOT EXISTS self_modification_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES self_modification_requests(id),
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'prompt',
        'policy',
        'config',
        'code_patch',
        'rule'
    )),
    artifact_ref TEXT NOT NULL,
    artifact_hash TEXT NOT NULL UNIQUE,
    generated_by TEXT NOT NULL,
    generation_method TEXT NOT NULL,
    rationale TEXT NOT NULL,
    diff_summary TEXT,
    protected_surface_check_result TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending',
        'under_review',
        'approved_for_validation',
        'validation_passed',
        'validation_failed',
        'approved_for_promotion',
        'rejected',
        'promoted',
        'rolled_back'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_self_modification_candidates_request_id ON self_modification_candidates(request_id);
CREATE INDEX IF NOT EXISTS idx_self_modification_candidates_status ON self_modification_candidates(status);
CREATE INDEX IF NOT EXISTS idx_self_modification_candidates_artifact_hash ON self_modification_candidates(artifact_hash);


-- Validation results
CREATE TABLE IF NOT EXISTS self_modification_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES self_modification_candidates(id),
    validation_type TEXT NOT NULL CHECK (validation_type IN (
        'protected_surface_scan',
        'static_analysis',
        'type_checking',
        'unit_tests',
        'integration_tests',
        'security_scan',
        'sandbox_execution',
        'regression_comparison',
        'eval_harness'
    )),
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed', 'warning', 'skipped')),
    logs_ref TEXT,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    issues_found JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_self_modification_validations_candidate_id ON self_modification_validations(candidate_id);
CREATE INDEX IF NOT EXISTS idx_self_modification_validations_validation_type ON self_modification_validations(validation_type);


-- Protected surfaces that cannot be modified
CREATE TABLE IF NOT EXISTS protected_surfaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    surface_name TEXT NOT NULL UNIQUE,
    component TEXT NOT NULL,
    description TEXT,
    protection_level TEXT NOT NULL CHECK (protection_level IN (
        'sealed',
        'monitored',
        'immutable',
        'audited'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Initialize protected surfaces
INSERT INTO protected_surfaces (surface_name, component, protection_level) VALUES
('calibration_scoring', 'calibration', 'sealed'),
('sealed_resolver_internals', 'resolution', 'sealed'),
('ground_truth_data', 'beliefs', 'immutable'),
('resolution_independence_engine', 'resolution', 'sealed'),
('audit_log_immutability', 'audit', 'immutable'),
('production_secret_checks', 'security', 'sealed'),
('rbac_enforcement', 'security', 'monitored'),
('governance_approval_checks', 'governance', 'monitored')
ON CONFLICT DO NOTHING;


-- Check if candidate touches protected surfaces
CREATE OR REPLACE FUNCTION check_protected_surface_modification(
    p_candidate_id UUID
) RETURNS TABLE(touches_protected BOOLEAN, protected_surfaces TEXT[], severity TEXT) AS $$
DECLARE
    v_artifact_hash TEXT;
    v_protected_surfaces TEXT[] := ARRAY[]::TEXT[];
    v_severity TEXT := 'info';
BEGIN
    SELECT artifact_hash INTO v_artifact_hash
    FROM self_modification_candidates WHERE id = p_candidate_id;

    -- In production, this would analyze the actual artifact/diff
    -- For now, return sample structure
    RETURN QUERY SELECT
        false,
        v_protected_surfaces,
        v_severity;
END;
$$ LANGUAGE plpgsql;


-- Immutable: candidates and validations
CREATE TRIGGER self_modification_candidates_immutable_after_created
    BEFORE UPDATE ON self_modification_candidates
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('self_modification_candidates');

CREATE TRIGGER self_modification_validations_immutable_after_created
    BEFORE UPDATE ON self_modification_validations
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('self_modification_validations');
