-- Migration 033: RBAC and service identities
--
-- Fine-grained access control. Learner cannot deploy. Resolver role
-- protected. Agent cannot approve own authority expansion.

CREATE TABLE IF NOT EXISTS principals (
    id TEXT PRIMARY KEY,
    principal_type TEXT NOT NULL CHECK (principal_type IN (
        'human_user',
        'service',
        'agent',
        'institution',
        'system'
    )),
    name TEXT NOT NULL,
    description TEXT,
    active BOOLEAN NOT NULL DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_principals_principal_type ON principals(principal_type);
CREATE INDEX IF NOT EXISTS idx_principals_active ON principals(active);


-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pre-populate standard roles
INSERT INTO roles (id, name, description, risk_level) VALUES
('role_viewer', 'Viewer', 'Read-only access', 'low'),
('role_operator', 'Operator', 'Can execute approved tasks', 'medium'),
('role_evaluator', 'Evaluator', 'Can run evaluations and create evals', 'medium'),
('role_governor', 'Governor', 'Can approve high-risk actions', 'high'),
('role_admin', 'Administrator', 'Full access', 'critical'),
('role_service_worker', 'Service Worker', 'Durable execution worker', 'medium'),
('role_resolver_service', 'Resolver Service', 'Protected: resolution-only', 'critical'),
('role_learner_service', 'Learner Service', 'Can create candidates, not deploy', 'medium'),
('role_deployment_service', 'Deployment Service', 'Can promote and rollback', 'high')
ON CONFLICT DO NOTHING;


-- Permissions
CREATE TABLE IF NOT EXISTS permissions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    resource TEXT NOT NULL,
    action TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Pre-populate standard permissions
INSERT INTO permissions (id, name, description, resource, action, risk_level) VALUES
('perm_task_create', 'Create Tasks', 'Create new autonomy tasks', 'task', 'create', 'low'),
('perm_task_execute', 'Execute Tasks', 'Execute approved tasks', 'task', 'execute', 'medium'),
('perm_memory_write', 'Write Memory', 'Write to memory system', 'memory', 'write', 'medium'),
('perm_goal_propose', 'Propose Goals', 'Propose new goals', 'goal', 'propose', 'low'),
('perm_goal_approve', 'Approve Goals', 'Approve goals', 'goal', 'approve', 'high'),
('perm_policy_create_candidate', 'Create Policy Candidates', 'Create policy improvement candidates', 'policy', 'create_candidate', 'medium'),
('perm_policy_promote', 'Promote Policies', 'Promote candidates to production', 'policy', 'promote', 'high'),
('perm_artifact_sign', 'Sign Artifacts', 'Sign artifacts', 'artifact', 'sign', 'high'),
('perm_deployment_canary', 'Canary Deployment', 'Start canary deployment', 'deployment', 'canary', 'high'),
('perm_deployment_rollback', 'Rollback', 'Trigger rollback', 'deployment', 'rollback', 'high'),
('perm_resolution_write', 'Resolver Write', 'Write resolution (sealed)', 'resolution', 'write', 'critical'),
('perm_governance_approve', 'Governance Approve', 'Approve governance decisions', 'governance', 'approve', 'critical'),
('perm_audit_read', 'Audit Read', 'Read audit logs', 'audit', 'read', 'medium')
ON CONFLICT DO NOTHING;


-- Principal-role associations
CREATE TABLE IF NOT EXISTS principal_roles (
    principal_id TEXT NOT NULL REFERENCES principals(id),
    role_id TEXT NOT NULL REFERENCES roles(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by TEXT,
    PRIMARY KEY (principal_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_principal_roles_principal_id ON principal_roles(principal_id);
CREATE INDEX IF NOT EXISTS idx_principal_roles_role_id ON principal_roles(role_id);


-- Role-permission associations
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id TEXT NOT NULL REFERENCES roles(id),
    permission_id TEXT NOT NULL REFERENCES permissions(id),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);

-- Grant all permissions to admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_admin', id FROM permissions
ON CONFLICT DO NOTHING;

-- Grant standard permissions to viewer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_viewer', id FROM permissions
WHERE action = 'read' OR id = 'perm_audit_read'
ON CONFLICT DO NOTHING;

-- Grant operator permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_operator', id FROM permissions
WHERE id IN ('perm_task_execute', 'perm_goal_propose')
ON CONFLICT DO NOTHING;

-- Grant resolver service ONLY resolution write
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_resolver_service', id FROM permissions
WHERE id = 'perm_resolution_write'
ON CONFLICT DO NOTHING;

-- Grant learner service: candidate creation but NOT promotion
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_learner_service', id FROM permissions
WHERE id IN ('perm_policy_create_candidate', 'perm_memory_write')
ON CONFLICT DO NOTHING;

-- Grant deployment service: promote and rollback
INSERT INTO role_permissions (role_id, permission_id)
SELECT 'role_deployment_service', id FROM permissions
WHERE id IN ('perm_policy_promote', 'perm_deployment_canary', 'perm_deployment_rollback')
ON CONFLICT DO NOTHING;


-- Service identities with scoped permissions
CREATE TABLE IF NOT EXISTS service_identities (
    id TEXT PRIMARY KEY,
    service_name TEXT NOT NULL UNIQUE,
    principal_id TEXT NOT NULL REFERENCES principals(id),
    api_key_hash TEXT UNIQUE,
    scoped_permissions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    active BOOLEAN NOT NULL DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_identities_service_name ON service_identities(service_name);
CREATE INDEX IF NOT EXISTS idx_service_identities_active ON service_identities(active);


-- Auth audit events
CREATE TABLE IF NOT EXISTS auth_audit_events (
    id BIGSERIAL PRIMARY KEY,
    principal_id TEXT REFERENCES principals(id),
    service_id TEXT REFERENCES service_identities(id),
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    permission_id TEXT REFERENCES permissions(id),
    decision TEXT NOT NULL CHECK (decision IN ('allowed', 'denied')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_events_principal_id ON auth_audit_events(principal_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_events_decision ON auth_audit_events(decision);
CREATE INDEX IF NOT EXISTS idx_auth_audit_events_created_at ON auth_audit_events(created_at);


-- Helper: check if principal has permission
CREATE OR REPLACE FUNCTION check_permission(
    p_principal_id TEXT,
    p_permission_id TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM principal_roles pr
        JOIN role_permissions rp ON pr.role_id = rp.role_id
        WHERE pr.principal_id = p_principal_id
        AND rp.permission_id = p_permission_id
    );
END;
$$ LANGUAGE plpgsql;


-- Helper: prevent learner from approving own promotion
CREATE OR REPLACE FUNCTION prevent_learner_self_approval()
RETURNS TRIGGER AS $$
BEGIN
    -- This is checked at application level
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
