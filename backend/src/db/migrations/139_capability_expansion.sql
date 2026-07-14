-- Migration 139: Capability and domain expansion (build phase C11).
--
-- The full expansion gate: proposed -> risk_review -> benchmark_design ->
-- limited_trial -> calibration_review -> governance_review -> approved |
-- restricted | rejected -> monitored -> expanded | revoked. A domain or
-- capability is admitted only after every stage plus a competence proof and an
-- independent governance approval. Capability grants are versioned and scoped;
-- restriction changes routing immediately; revocation blocks new work.
--
-- Consumes the existing proof_of_competence / domain_registry machinery; it
-- does not replace them.

CREATE TABLE IF NOT EXISTS expansion_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  expansion_type TEXT NOT NULL CHECK (expansion_type IN ('domain_onboarding','capability_expansion')),
  domain_key TEXT NOT NULL,
  capability_key TEXT,
  title TEXT NOT NULL,
  proposer_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  competence_proof_id TEXT,
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','risk_review','benchmark_design','limited_trial','calibration_review',
                      'governance_review','approved','restricted','rejected','monitored','expanded','revoked')),
  reject_reason TEXT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_expansion_proposals_status ON expansion_proposals (civilization_id, status);

CREATE TABLE IF NOT EXISTS expansion_stage_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES expansion_proposals(id) ON DELETE RESTRICT,
  stage TEXT NOT NULL
    CHECK (stage IN ('risk_review','benchmark_design','limited_trial','calibration_review','governance_review')),
  passed BOOLEAN NOT NULL,
  summary TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proposal_id, stage)
);

CREATE TABLE IF NOT EXISTS expansion_proposal_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES expansion_proposals(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  capability_key TEXT NOT NULL,
  domain_key TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  current_version INTEGER NOT NULL DEFAULT 1,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, capability_key, domain_key)
);

CREATE TABLE IF NOT EXISTS capability_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  capability_id UUID NOT NULL REFERENCES capabilities(id) ON DELETE RESTRICT,
  proposal_id UUID REFERENCES expansion_proposals(id),
  grantee_scope_type TEXT NOT NULL CHECK (grantee_scope_type IN ('institution','citizen','society')),
  grantee_scope_id TEXT NOT NULL,
  domain_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','restricted','revoked')),
  restriction_json JSONB,
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  restricted_by_actor_id UUID REFERENCES actors(id),
  restricted_at TIMESTAMPTZ,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_capability_grant_live
  ON capability_grants (capability_id, grantee_scope_type, grantee_scope_id, domain_key)
  WHERE status <> 'revoked';
CREATE INDEX IF NOT EXISTS idx_capability_grants_lookup
  ON capability_grants (grantee_scope_type, grantee_scope_id, status);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION expansion_proposal_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('rejected','expanded','revoked') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'EXPANSION GUARD: % proposal is terminal', OLD.status;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.expansion_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'EXPANSION GUARD: proposal status may only change through the expansion service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.proposer_actor_id IS DISTINCT FROM OLD.proposer_actor_id
     OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'EXPANSION GUARD: proposal identity fields are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_expansion_proposal_guard ON expansion_proposals;
CREATE TRIGGER trg_expansion_proposal_guard
  BEFORE UPDATE ON expansion_proposals
  FOR EACH ROW EXECUTE FUNCTION expansion_proposal_guard();

CREATE OR REPLACE FUNCTION capability_grant_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.capability_id IS DISTINCT FROM OLD.capability_id
     OR NEW.grantee_scope_type IS DISTINCT FROM OLD.grantee_scope_type
     OR NEW.grantee_scope_id IS DISTINCT FROM OLD.grantee_scope_id
     OR NEW.domain_key IS DISTINCT FROM OLD.domain_key
     OR NEW.granted_by_actor_id IS DISTINCT FROM OLD.granted_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'EXPANSION GUARD: capability grant identity fields are immutable';
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
       (OLD.status = 'active' AND NEW.status IN ('restricted','revoked'))
    OR (OLD.status = 'restricted' AND NEW.status IN ('active','revoked'))) THEN
    RAISE EXCEPTION 'EXPANSION GUARD: illegal grant status transition % -> %', OLD.status, NEW.status;
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_capability_grant_guard ON capability_grants;
CREATE TRIGGER trg_capability_grant_guard
  BEFORE UPDATE ON capability_grants
  FOR EACH ROW EXECUTE FUNCTION capability_grant_guard();

DROP TRIGGER IF EXISTS trg_expansion_stage_append_only ON expansion_stage_records;
CREATE TRIGGER trg_expansion_stage_append_only
  BEFORE UPDATE ON expansion_stage_records FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_expansion_transitions_append_only ON expansion_proposal_transitions;
CREATE TRIGGER trg_expansion_transitions_append_only
  BEFORE UPDATE ON expansion_proposal_transitions FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c11_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C11 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'expansion_proposals','expansion_stage_records','expansion_proposal_transitions','capabilities','capability_grants'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c11_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON expansion_stage_records, expansion_proposal_transitions FROM PUBLIC;
REVOKE DELETE ON expansion_proposals, capabilities, capability_grants FROM PUBLIC;
