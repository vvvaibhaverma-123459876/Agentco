-- Migration 079: L1 identity and authority substrate.
--
-- Canonical civilization actors, roles, permissions, and role assignments.
-- This is additive to the older governance_* RBAC tables; it does not weaken
-- existing governance permissions.

CREATE TABLE IF NOT EXISTS actors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_type TEXT NOT NULL CHECK (
    actor_type IN (
      'human',
      'agent',
      'service',
      'institution',
      'external_system',
      'resolver',
      'auditor',
      'governor'
    )
  ),
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_actors_type ON actors(actor_type);
CREATE INDEX IF NOT EXISTS idx_actors_status ON actors(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_actors_active_name_type
  ON actors(actor_type, name)
  WHERE status = 'active';

CREATE TABLE IF NOT EXISTS agent_identities (
  actor_id UUID PRIMARY KEY REFERENCES actors(id) ON DELETE RESTRICT,
  agent_key TEXT NOT NULL UNIQUE,
  model_name TEXT NOT NULL,
  version TEXT NOT NULL,
  owner_institution_id UUID,
  public_key BYTEA,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_identities_status ON agent_identities(status);

CREATE TABLE IF NOT EXISTS service_identities (
  actor_id UUID PRIMARY KEY REFERENCES actors(id) ON DELETE RESTRICT,
  service_name TEXT NOT NULL UNIQUE,
  scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'revoked')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_identities_status ON service_identities(status);

CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_name TEXT NOT NULL UNIQUE,
  description TEXT,
  risk_tier INTEGER NOT NULL DEFAULT 1 CHECK (risk_tier BETWEEN 0 AND 3),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  protected_surface TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS role_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  role_id UUID NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
  institution_id UUID,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to TIMESTAMPTZ,
  assigned_by UUID REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (valid_to IS NULL OR valid_to > valid_from)
);

CREATE INDEX IF NOT EXISTS idx_role_assignments_actor ON role_assignments(actor_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_role ON role_assignments(role_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_role_assignments_active_unique
  ON role_assignments(actor_id, role_id, COALESCE(institution_id, '00000000-0000-0000-0000-000000000000'::uuid))
  WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS actor_permissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL DEFAULT '*',
  granted_by UUID REFERENCES actors(id) ON DELETE RESTRICT,
  expires_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_actor_permissions_actor ON actor_permissions(actor_id);
CREATE INDEX IF NOT EXISTS idx_actor_permissions_permission ON actor_permissions(permission_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_actor_permissions_active_unique
  ON actor_permissions(actor_id, permission_id, scope)
  WHERE revoked_at IS NULL;

INSERT INTO roles (role_name, description, risk_tier) VALUES
  ('claim_maker', 'Can make evidence-backed claims', 1),
  ('resolver', 'Can resolve predictions produced by a distinct actor', 2),
  ('auditor', 'Can inspect and attest audit trails', 1),
  ('governor', 'Can approve protected governance actions', 3),
  ('memory_keeper', 'Can promote reality-validated memory', 2),
  ('task_executor', 'Can execute assigned civilization tasks', 1)
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO permissions (name, description, protected_surface) VALUES
  ('claim.register', 'Register evidence-backed claims', 'claim_registration'),
  ('prediction.resolve', 'Resolve predictions as an independent resolver', 'prediction_resolution'),
  ('audit.read', 'Read audit and event trails', 'audit_access'),
  ('memory.promote', 'Promote reality-validated memories', 'memory_promotion'),
  ('task.execute', 'Execute assigned civilization tasks', 'task_execution'),
  ('governance.approve', 'Approve protected governance actions', 'governance_approval')
ON CONFLICT (name) DO NOTHING;
