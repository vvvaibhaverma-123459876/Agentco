-- Migration 102: L13 domain registry.
--
-- Domains can be activated only after a core institution exists and a trust
-- score proves competence for the domain.

CREATE TABLE IF NOT EXISTS domain_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('proposed', 'active', 'suspended', 'rejected')),
  institution_id VARCHAR(36) NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  institution_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  proof_subject_id TEXT NOT NULL,
  required_trust_threshold NUMERIC NOT NULL DEFAULT 0.7 CHECK (required_trust_threshold >= 0 AND required_trust_threshold <= 1),
  latest_trust_id UUID NOT NULL REFERENCES trust_scores(trust_id) ON DELETE RESTRICT,
  latest_trust_factor NUMERIC NOT NULL CHECK (latest_trust_factor >= 0 AND latest_trust_factor <= 1),
  proof_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_domain_registry_status
  ON domain_registry(status);
CREATE INDEX IF NOT EXISTS idx_domain_registry_institution
  ON domain_registry(institution_id);
CREATE INDEX IF NOT EXISTS idx_domain_registry_trust
  ON domain_registry(latest_trust_id);
