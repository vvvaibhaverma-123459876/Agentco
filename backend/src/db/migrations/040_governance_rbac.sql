-- Migration 040: Governance RBAC (Role-Based Access Control)
--
-- Implements role-based access control for civilization trust governance operations.
-- Defines 5 governance roles with specific permissions and audit trails.
--
-- Roles (5 levels):
-- 1. governance_viewer    - Read-only access to governance state
-- 2. governance_operator  - Can manage operational aspects (metrics, monitoring)
-- 3. governance_reviewer  - Can review and evaluate policies
-- 4. governance_approver  - Can approve/reject policies (multi-level approval)
-- 5. governance_admin     - Full control including role assignments

-- ============================================================
-- GOVERNANCE ROLES TABLE
-- ============================================================

DROP TABLE IF EXISTS governance_roles CASCADE;
CREATE TABLE governance_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    permission_level INTEGER NOT NULL CHECK (permission_level >= 1 AND permission_level <= 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_governance_roles_name ON governance_roles(role_name);
CREATE INDEX idx_governance_roles_level ON governance_roles(permission_level);

-- Insert standard governance roles
INSERT INTO governance_roles (role_name, display_name, description, permission_level) VALUES
    ('governance_viewer', 'Governance Viewer', 'Read-only access to governance state, policies, and audit trail', 1),
    ('governance_operator', 'Governance Operator', 'Can manage operational aspects like metrics and monitoring', 2),
    ('governance_reviewer', 'Governance Reviewer', 'Can review policies and create evaluations', 3),
    ('governance_approver', 'Governance Approver', 'Can approve or reject governance policies', 4),
    ('governance_admin', 'Governance Administrator', 'Full control over governance system and role assignments', 5)
ON CONFLICT (role_name) DO NOTHING;

-- ============================================================
-- PERMISSIONS TABLE
-- ============================================================

DROP TABLE IF EXISTS governance_permissions CASCADE;
CREATE TABLE governance_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permission_name TEXT NOT NULL UNIQUE,
    description TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_governance_permissions_resource ON governance_permissions(resource);
CREATE INDEX idx_governance_permissions_action ON governance_permissions(action);

-- Insert standard governance permissions
INSERT INTO governance_permissions (permission_name, description, resource, action) VALUES
    ('governance.view_policies', 'View trust policies', 'trust_policies', 'read'),
    ('governance.view_constitution', 'View constitution and protected surfaces', 'constitution', 'read'),
    ('governance.view_audit_trail', 'View governance audit trail and reputation ledger', 'audit_trail', 'read'),
    ('governance.view_drift', 'View drift events and monitoring data', 'drift_monitor', 'read'),
    ('governance.record_metrics', 'Record canary metrics and deployment metrics', 'canary_metrics', 'write'),
    ('governance.review_policies', 'Create and submit policy reviews', 'policy_reviews', 'write'),
    ('governance.approve_policies', 'Approve or reject governance policies', 'policy_approval', 'write'),
    ('governance.manage_emergency_freeze', 'Activate or deactivate emergency freeze', 'emergency_freeze', 'write'),
    ('governance.modify_constitution', 'Modify constitution (add/remove rules)', 'constitution', 'write'),
    ('governance.assign_roles', 'Assign governance roles to entities', 'role_assignment', 'write')
ON CONFLICT (permission_name) DO NOTHING;

-- ============================================================
-- ROLE PERMISSIONS MAPPING
-- ============================================================

DROP TABLE IF EXISTS governance_role_permissions CASCADE;
CREATE TABLE governance_role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES governance_roles(id),
    permission_id UUID NOT NULL REFERENCES governance_permissions(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role ON governance_role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission ON governance_role_permissions(permission_id);

-- Define role-permission mappings
-- viewer: read-only access
INSERT INTO governance_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM governance_roles r, governance_permissions p
WHERE r.role_name = 'governance_viewer'
AND p.permission_name IN (
    'governance.view_policies',
    'governance.view_constitution',
    'governance.view_audit_trail',
    'governance.view_drift'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- operator: read + metrics
INSERT INTO governance_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM governance_roles r, governance_permissions p
WHERE r.role_name = 'governance_operator'
AND p.permission_name IN (
    'governance.view_policies',
    'governance.view_constitution',
    'governance.view_audit_trail',
    'governance.view_drift',
    'governance.record_metrics'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- reviewer: read + reviews
INSERT INTO governance_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM governance_roles r, governance_permissions p
WHERE r.role_name = 'governance_reviewer'
AND p.permission_name IN (
    'governance.view_policies',
    'governance.view_constitution',
    'governance.view_audit_trail',
    'governance.view_drift',
    'governance.review_policies',
    'governance.record_metrics'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- approver: read + reviews + approvals
INSERT INTO governance_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM governance_roles r, governance_permissions p
WHERE r.role_name = 'governance_approver'
AND p.permission_name IN (
    'governance.view_policies',
    'governance.view_constitution',
    'governance.view_audit_trail',
    'governance.view_drift',
    'governance.review_policies',
    'governance.approve_policies',
    'governance.record_metrics',
    'governance.manage_emergency_freeze'
)
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- admin: all permissions
INSERT INTO governance_role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM governance_roles r, governance_permissions p
WHERE r.role_name = 'governance_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- ============================================================
-- ENTITY ROLE ASSIGNMENTS
-- ============================================================

DROP TABLE IF EXISTS governance_entity_roles CASCADE;
CREATE TABLE governance_entity_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'service',
    role_id UUID NOT NULL REFERENCES governance_roles(id),
    assigned_by TEXT,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    UNIQUE(entity_id, role_id)
);

CREATE INDEX idx_entity_roles_entity ON governance_entity_roles(entity_id);
CREATE INDEX idx_entity_roles_role ON governance_entity_roles(role_id);
CREATE INDEX idx_entity_roles_active ON governance_entity_roles(revoked_at);

-- ============================================================
-- RBAC AUDIT LOG
-- ============================================================

DROP TABLE IF EXISTS governance_rbac_audit CASCADE;
CREATE TABLE governance_rbac_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    resource_id UUID,
    permission_granted BOOLEAN NOT NULL,
    required_permission TEXT,
    reason_denied TEXT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rbac_audit_actor ON governance_rbac_audit(actor_entity_id);
CREATE INDEX idx_rbac_audit_action ON governance_rbac_audit(action);
CREATE INDEX idx_rbac_audit_granted ON governance_rbac_audit(permission_granted);
CREATE INDEX idx_rbac_audit_created ON governance_rbac_audit(created_at DESC);

-- ============================================================
-- RBAC HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION get_entity_roles(p_entity_id TEXT)
RETURNS TABLE(role_name TEXT, display_name TEXT, permission_level INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT r.role_name, r.display_name, r.permission_level
    FROM governance_entity_roles er
    JOIN governance_roles r ON er.role_id = r.id
    WHERE er.entity_id = p_entity_id
    AND er.revoked_at IS NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION has_permission(p_entity_id TEXT, p_permission_name TEXT)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_permission BOOLEAN;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM governance_entity_roles er
        JOIN governance_role_permissions rp ON er.role_id = rp.role_id
        JOIN governance_permissions p ON rp.permission_id = p.id
        WHERE er.entity_id = p_entity_id
        AND p.permission_name = p_permission_name
        AND er.revoked_at IS NULL
    ) INTO v_has_permission;
    RETURN v_has_permission;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION audit_rbac_check(
    p_actor_entity_id TEXT,
    p_action TEXT,
    p_resource TEXT,
    p_permission_granted BOOLEAN,
    p_required_permission TEXT DEFAULT NULL,
    p_reason_denied TEXT DEFAULT NULL,
    p_trace_id TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_audit_id UUID;
BEGIN
    INSERT INTO governance_rbac_audit (
        actor_entity_id, action, resource, permission_granted,
        required_permission, reason_denied, trace_id
    ) VALUES (
        p_actor_entity_id, p_action, p_resource, p_permission_granted,
        p_required_permission, p_reason_denied, p_trace_id
    ) RETURNING id INTO v_audit_id;
    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- IMMUTABILITY TRIGGER FOR ROLE ASSIGNMENTS
-- ============================================================

DROP TRIGGER IF EXISTS entity_roles_immutable ON governance_entity_roles;
CREATE TRIGGER entity_roles_immutable
    BEFORE UPDATE ON governance_entity_roles
    FOR EACH ROW
    WHEN (OLD.revoked_at IS NULL)
    EXECUTE FUNCTION raise_immutability_violation('governance_entity_roles (non-revoked)');

-- ============================================================
-- IMMUTABILITY TRIGGER FOR AUDIT LOG
-- ============================================================

DROP TRIGGER IF EXISTS rbac_audit_immutable ON governance_rbac_audit;
CREATE TRIGGER rbac_audit_immutable
    BEFORE UPDATE ON governance_rbac_audit
    FOR EACH ROW
    EXECUTE FUNCTION raise_immutability_violation('governance_rbac_audit');
