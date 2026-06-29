-- Migration 084: L1 authority chain.
--
-- Adds role-derived permission mapping, delegation grants, and persisted
-- authority decision provenance. Decisions remain append-only and emit
-- canonical event_log entries through the identity service.

CREATE TABLE IF NOT EXISTS role_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL DEFAULT '*',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (role_id, permission_id, scope)
);

CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON role_permissions(permission_id);

CREATE TABLE IF NOT EXISTS authority_delegation_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  principal_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  delegate_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL DEFAULT '*',
  granted_by UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (principal_actor_id <> delegate_actor_id),
  CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_authority_delegations_delegate
  ON authority_delegation_grants(delegate_actor_id, permission_id, scope)
  WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_authority_delegations_principal
  ON authority_delegation_grants(principal_actor_id, created_at DESC);

CREATE TABLE IF NOT EXISTS authority_decision_chains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  requested_actor_id TEXT NOT NULL DEFAULT '',
  permission_id UUID REFERENCES permissions(id) ON DELETE RESTRICT,
  permission_name TEXT NOT NULL,
  scope TEXT NOT NULL,
  allowed BOOLEAN NOT NULL,
  reason TEXT NOT NULL,
  chain JSONB NOT NULL,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_authority_decision_chains_actor
  ON authority_decision_chains(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_authority_decision_chains_requested_actor
  ON authority_decision_chains(requested_actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_authority_decision_chains_permission
  ON authority_decision_chains(permission_name, scope, created_at DESC);

INSERT INTO role_permissions (role_id, permission_id, scope)
SELECT r.id, p.id, '*'
  FROM (VALUES
    ('claim_maker', 'claim.register'),
    ('resolver', 'prediction.resolve'),
    ('auditor', 'audit.read'),
    ('governor', 'governance.approve'),
    ('memory_keeper', 'memory.promote'),
    ('task_executor', 'task.execute')
  ) AS mapping(role_name, permission_name)
  JOIN roles r ON r.role_name = mapping.role_name
  JOIN permissions p ON p.name = mapping.permission_name
ON CONFLICT (role_id, permission_id, scope) DO NOTHING;

REVOKE DELETE ON role_permissions FROM PUBLIC;
REVOKE DELETE ON authority_delegation_grants FROM PUBLIC;
REVOKE DELETE ON authority_decision_chains FROM PUBLIC;
