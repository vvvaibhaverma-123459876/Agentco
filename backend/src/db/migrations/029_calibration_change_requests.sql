-- Migration 029: Calibration Change Governance
--
-- Implements the governance workflow for proposed calibration changes.
-- Changes are validated against constitution, evaluated for impact, and
-- require governance approval before becoming trust policies.
--
-- Change request lifecycle: draft → under_review → impact_assessment → approval_required → approved/rejected → canary → active/rolled_back

-- ============================================================
-- CHANGE REQUEST STATUS & TYPE ENUMS
-- ============================================================

DROP TYPE IF EXISTS change_request_status CASCADE;
CREATE TYPE change_request_status AS ENUM (
    'draft', 'under_review', 'impact_assessment', 'approval_required',
    'approved', 'rejected', 'canary', 'active', 'rolled_back', 'cancelled'
);

DROP TYPE IF EXISTS change_risk_level CASCADE;
CREATE TYPE change_risk_level AS ENUM (
    'critical', 'high', 'medium', 'low'
);

-- ============================================================
-- CALIBRATION CHANGE REQUESTS TABLE
-- ============================================================

DROP TABLE IF EXISTS calibration_change_requests CASCADE;
CREATE TABLE calibration_change_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requester_entity_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    affected_tables TEXT[],
    affected_columns TEXT[],
    proposed_change_json JSONB NOT NULL,
    risk_level change_risk_level NOT NULL DEFAULT 'medium',
    status change_request_status NOT NULL DEFAULT 'draft',
    constitution_id UUID REFERENCES calibration_constitution_versions(id),
    requires_rollback_plan BOOLEAN NOT NULL DEFAULT true,
    rollback_plan_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    submitted_for_review_at TIMESTAMPTZ,
    impact_assessment_started_at TIMESTAMPTZ,
    impact_assessment_completed_at TIMESTAMPTZ,
    approval_requested_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    approved_by_entity_id TEXT,
    rejected_at TIMESTAMPTZ,
    rejected_by_entity_id TEXT,
    rejection_reason TEXT,
    trace_id TEXT
);

CREATE INDEX idx_change_requests_requester ON calibration_change_requests(requester_entity_id);
CREATE INDEX idx_change_requests_status ON calibration_change_requests(status);
CREATE INDEX idx_change_requests_risk ON calibration_change_requests(risk_level);
CREATE INDEX idx_change_requests_type ON calibration_change_requests(change_type);
CREATE INDEX idx_change_requests_created_at ON calibration_change_requests(created_at);

-- ============================================================
-- CONSTITUTION VALIDATION CHECKS TABLE
-- ============================================================

DROP TABLE IF EXISTS constitution_compliance_checks CASCADE;
CREATE TABLE constitution_compliance_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_request_id UUID NOT NULL REFERENCES calibration_change_requests(id),
    constitution_id UUID NOT NULL REFERENCES calibration_constitution_versions(id),
    check_result TEXT NOT NULL,
    is_compliant BOOLEAN NOT NULL,
    violations TEXT[],
    protected_surfaces_touched TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_compliance_checks_request ON constitution_compliance_checks(change_request_id);
CREATE INDEX idx_compliance_checks_constitution ON constitution_compliance_checks(constitution_id);
CREATE INDEX idx_compliance_checks_result ON constitution_compliance_checks(check_result);

-- ============================================================
-- CHANGE APPROVAL RECORDS TABLE
-- ============================================================

DROP TABLE IF EXISTS change_approvals CASCADE;
CREATE TABLE change_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_request_id UUID NOT NULL REFERENCES calibration_change_requests(id),
    approver_entity_id TEXT NOT NULL,
    approver_role TEXT,
    approval_scope TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected', 'deferred')),
    reason TEXT,
    quorum_required INT,
    quorum_met BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_approvals_request ON change_approvals(change_request_id);
CREATE INDEX idx_approvals_approver ON change_approvals(approver_entity_id);
CREATE INDEX idx_approvals_decision ON change_approvals(decision);

-- ============================================================
-- CONVERSION TO TRUST POLICY TABLE
-- ============================================================

DROP TABLE IF EXISTS change_to_policy_conversions CASCADE;
CREATE TABLE change_to_policy_conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_request_id UUID NOT NULL REFERENCES calibration_change_requests(id),
    policy_id UUID REFERENCES trust_policy_versions(id),
    conversion_timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_conversions_change ON change_to_policy_conversions(change_request_id);
CREATE INDEX idx_conversions_policy ON change_to_policy_conversions(policy_id);

-- ============================================================
-- CHANGE REQUEST EVENTS (AUDIT TRAIL)
-- ============================================================

DROP TABLE IF EXISTS change_request_events CASCADE;
CREATE TABLE change_request_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_request_id UUID NOT NULL REFERENCES calibration_change_requests(id),
    event_type TEXT NOT NULL,
    previous_status change_request_status,
    new_status change_request_status NOT NULL,
    actor_entity_id UUID,
    actor_role TEXT,
    reason TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_change_events_request ON change_request_events(change_request_id);
CREATE INDEX idx_change_events_type ON change_request_events(event_type);
CREATE INDEX idx_change_events_status ON change_request_events(new_status);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS change_requests_immutable_final ON calibration_change_requests;
CREATE TRIGGER change_requests_immutable_final
    BEFORE UPDATE ON calibration_change_requests
    FOR EACH ROW
    WHEN (OLD.status IN ('approved', 'rejected', 'active', 'rolled_back'))
    EXECUTE FUNCTION raise_immutability_violation('calibration_change_requests in final state');

DROP TRIGGER IF EXISTS compliance_checks_immutable ON constitution_compliance_checks;
CREATE TRIGGER compliance_checks_immutable
    BEFORE UPDATE ON constitution_compliance_checks
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('constitution_compliance_checks');

DROP TRIGGER IF EXISTS approvals_immutable ON change_approvals;
CREATE TRIGGER approvals_immutable
    BEFORE UPDATE ON change_approvals
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('change_approvals');

DROP TRIGGER IF EXISTS change_events_immutable ON change_request_events;
CREATE TRIGGER change_events_immutable
    BEFORE UPDATE ON change_request_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('change_request_events');

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION is_change_type_allowed(
    p_constitution_id UUID,
    p_change_type TEXT
)
RETURNS BOOLEAN AS $$
DECLARE
    v_is_prohibited BOOLEAN;
    v_is_allowed BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM prohibited_change_types
        WHERE constitution_id = p_constitution_id
        AND change_type_name = p_change_type
    ) INTO v_is_prohibited;

    IF v_is_prohibited THEN
        RETURN false;
    END IF;

    SELECT EXISTS(
        SELECT 1 FROM allowed_change_types
        WHERE constitution_id = p_constitution_id
        AND change_type_name = p_change_type
    ) INTO v_is_allowed;

    RETURN v_is_allowed;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION check_change_request_ready_for_approval(p_change_request_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_rollback_plan BOOLEAN;
    v_has_compliance_check BOOLEAN;
    v_status change_request_status;
BEGIN
    SELECT status INTO v_status
    FROM calibration_change_requests
    WHERE id = p_change_request_id;

    IF v_status IS NULL THEN
        RETURN false;
    END IF;

    -- Must be in impact_assessment status
    IF v_status != 'impact_assessment' THEN
        RETURN false;
    END IF;

    -- Must have rollback plan if required
    SELECT requires_rollback_plan INTO v_has_rollback_plan
    FROM calibration_change_requests
    WHERE id = p_change_request_id;

    IF v_has_rollback_plan THEN
        SELECT rollback_plan_json INTO v_has_rollback_plan
        FROM calibration_change_requests
        WHERE id = p_change_request_id;

        IF v_has_rollback_plan IS NULL THEN
            RETURN false;
        END IF;
    END IF;

    -- Must have compliance check
    SELECT EXISTS(
        SELECT 1 FROM constitution_compliance_checks
        WHERE change_request_id = p_change_request_id
    ) INTO v_has_compliance_check;

    RETURN v_has_compliance_check;
END;
$$ LANGUAGE plpgsql;
