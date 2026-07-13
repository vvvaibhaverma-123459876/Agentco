-- Migration 131: Societies and institution governance completion (build phase C3).
--
-- Societies sit between the civilization root and institutions. Society
-- jurisdiction is a DB-enforced subset of civilization jurisdiction via a
-- composite foreign key. Institutions gain charters (append-only, versioned),
-- mandates/powers/limits (grant-style rows), civilization-wide jurisdiction
-- grants, society membership, and inter-institution contracts with lifecycle
-- and settlement.
--
-- institutions.id is VARCHAR in the legacy schema; every reference here
-- matches that type exactly.

CREATE TABLE IF NOT EXISTS societies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'forming'
    CHECK (status IN ('forming','active','suspended','dissolved')),
  description TEXT NOT NULL DEFAULT '',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, name)
);
CREATE INDEX IF NOT EXISTS idx_societies_status ON societies (civilization_id, status);

CREATE TABLE IF NOT EXISTS society_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id UUID NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS society_charters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id UUID NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  charter_json JSONB NOT NULL,
  charter_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','superseded')),
  activated_at TIMESTAMPTZ,
  activated_by_actor_id UUID REFERENCES actors(id),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (society_id, version_number)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_society_charter_single_active
  ON society_charters (society_id) WHERE status = 'active';

-- Society jurisdiction must be a subset of civilization jurisdiction:
-- the composite FK makes granting a key the civilization never granted
-- impossible at the DB layer.
CREATE TABLE IF NOT EXISTS society_jurisdictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id UUID NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
  civilization_id UUID NOT NULL,
  jurisdiction_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (civilization_id, jurisdiction_key)
    REFERENCES civilization_jurisdictions (civilization_id, jurisdiction_key),
  UNIQUE (society_id, jurisdiction_key)
);

CREATE TABLE IF NOT EXISTS society_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  society_id UUID NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
  citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  role_in_society TEXT NOT NULL DEFAULT 'member',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at TIMESTAMPTZ,
  ended_by_actor_id UUID REFERENCES actors(id),
  event_log_id UUID REFERENCES event_log(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_society_membership_active
  ON society_memberships (society_id, citizen_id) WHERE status = 'active';

-- An institution belongs to at most one active society…
CREATE TABLE IF NOT EXISTS institution_society_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  society_id UUID NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ended')),
  attached_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  ended_at TIMESTAMPTZ,
  ended_by_actor_id UUID REFERENCES actors(id),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_institution_society_active
  ON institution_society_memberships (institution_id) WHERE status = 'active';

-- …or holds an explicit civilization-wide jurisdiction grant.
CREATE TABLE IF NOT EXISTS institution_jurisdiction_grants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  civilization_id UUID NOT NULL,
  jurisdiction_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  FOREIGN KEY (civilization_id, jurisdiction_key)
    REFERENCES civilization_jurisdictions (civilization_id, jurisdiction_key),
  UNIQUE (institution_id, jurisdiction_key)
);

CREATE TABLE IF NOT EXISTS institution_charters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  charter_json JSONB NOT NULL,
  charter_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','superseded')),
  activated_at TIMESTAMPTZ,
  activated_by_actor_id UUID REFERENCES actors(id),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (institution_id, version_number)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_institution_charter_single_active
  ON institution_charters (institution_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS institution_mandates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  mandate_key TEXT NOT NULL,
  description TEXT NOT NULL,
  department_name TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_institution_mandate_active
  ON institution_mandates (institution_id, mandate_key) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS institution_powers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  power_key TEXT NOT NULL,
  scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  authorized_decision_ref TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_institution_power_active
  ON institution_powers (institution_id, power_key) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS institution_limits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  limit_key TEXT NOT NULL,
  limit_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_institution_limit_active
  ON institution_limits (institution_id, limit_key) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS inter_institution_contracts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  to_institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  terms_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  commitments_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','accepted','active','fulfilled','breached','terminated')),
  settlement_json JSONB,
  breach_reason TEXT,
  proposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  accepted_by_actor_id UUID REFERENCES actors(id),
  closed_by_actor_id UUID REFERENCES actors(id),
  closed_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (from_institution_id <> to_institution_id)
);
CREATE INDEX IF NOT EXISTS idx_inter_institution_contracts_status
  ON inter_institution_contracts (status);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION society_status_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'dissolved' THEN
    RAISE EXCEPTION 'SOCIETY GUARD: dissolved society % is immutable', OLD.id;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.society_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'SOCIETY GUARD: status may only change through the society service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.name IS DISTINCT FROM OLD.name OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'SOCIETY GUARD: identity columns are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_society_status_guard ON societies;
CREATE TRIGGER trg_society_status_guard
  BEFORE UPDATE ON societies
  FOR EACH ROW EXECUTE FUNCTION society_status_guard();

-- Society charters reuse the civilization charter guard semantics.
DROP TRIGGER IF EXISTS trg_society_charter_guard ON society_charters;
CREATE OR REPLACE FUNCTION society_charter_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.society_id IS DISTINCT FROM OLD.society_id
     OR NEW.version_number IS DISTINCT FROM OLD.version_number
     OR NEW.charter_json IS DISTINCT FROM OLD.charter_json
     OR NEW.charter_hash IS DISTINCT FROM OLD.charter_hash
     OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'SOCIETY GUARD: charter content is immutable';
  END IF;
  IF NOT ((OLD.status = 'draft' AND NEW.status = 'active')
       OR (OLD.status = 'active' AND NEW.status = 'superseded')
       OR (OLD.status = NEW.status)) THEN
    RAISE EXCEPTION 'SOCIETY GUARD: illegal charter status transition % -> %', OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_society_charter_guard
  BEFORE UPDATE ON society_charters
  FOR EACH ROW EXECUTE FUNCTION society_charter_guard();

DROP TRIGGER IF EXISTS trg_institution_charter_guard ON institution_charters;
CREATE OR REPLACE FUNCTION institution_charter_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.institution_id IS DISTINCT FROM OLD.institution_id
     OR NEW.version_number IS DISTINCT FROM OLD.version_number
     OR NEW.charter_json IS DISTINCT FROM OLD.charter_json
     OR NEW.charter_hash IS DISTINCT FROM OLD.charter_hash
     OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'INSTITUTION GUARD: charter content is immutable';
  END IF;
  IF NOT ((OLD.status = 'draft' AND NEW.status = 'active')
       OR (OLD.status = 'active' AND NEW.status = 'superseded')
       OR (OLD.status = NEW.status)) THEN
    RAISE EXCEPTION 'INSTITUTION GUARD: illegal charter status transition % -> %', OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_institution_charter_guard
  BEFORE UPDATE ON institution_charters
  FOR EACH ROW EXECUTE FUNCTION institution_charter_guard();

-- Grant-style rows (jurisdictions, memberships, mandates, powers, limits):
-- grant fields frozen; only active→revoked/ended with metadata.
CREATE OR REPLACE FUNCTION civilization_grant_row_guard() RETURNS trigger AS $$
DECLARE
  mutable TEXT[] := ARRAY['status','revoked_at','revoked_by_actor_id','ended_at','ended_by_actor_id'];
BEGIN
  -- Schema-agnostic immutability: any column change outside the explicit
  -- revocation/end metadata set is rejected.
  IF (to_jsonb(OLD) - mutable) <> (to_jsonb(NEW) - mutable) THEN
    RAISE EXCEPTION 'GRANT GUARD: % grant fields are immutable', TG_TABLE_NAME;
  END IF;
  IF NOT (OLD.status = 'active' AND NEW.status IN ('revoked','ended')) THEN
    RAISE EXCEPTION 'GRANT GUARD: illegal % status transition % -> %', TG_TABLE_NAME, OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_society_jurisdictions_guard ON society_jurisdictions;
CREATE TRIGGER trg_society_jurisdictions_guard
  BEFORE UPDATE ON society_jurisdictions
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_society_memberships_guard ON society_memberships;
CREATE TRIGGER trg_society_memberships_guard
  BEFORE UPDATE ON society_memberships
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_institution_society_memberships_guard ON institution_society_memberships;
CREATE TRIGGER trg_institution_society_memberships_guard
  BEFORE UPDATE ON institution_society_memberships
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_institution_jurisdiction_grants_guard ON institution_jurisdiction_grants;
CREATE TRIGGER trg_institution_jurisdiction_grants_guard
  BEFORE UPDATE ON institution_jurisdiction_grants
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_institution_mandates_guard ON institution_mandates;
CREATE TRIGGER trg_institution_mandates_guard
  BEFORE UPDATE ON institution_mandates
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_institution_powers_guard ON institution_powers;
CREATE TRIGGER trg_institution_powers_guard
  BEFORE UPDATE ON institution_powers
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();
DROP TRIGGER IF EXISTS trg_institution_limits_guard ON institution_limits;
CREATE TRIGGER trg_institution_limits_guard
  BEFORE UPDATE ON institution_limits
  FOR EACH ROW EXECUTE FUNCTION civilization_grant_row_guard();

-- Contract lifecycle guard: parties/title frozen always; terms frozen once
-- accepted; only legal transitions; closure metadata on terminal move.
CREATE OR REPLACE FUNCTION inter_institution_contract_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.from_institution_id IS DISTINCT FROM OLD.from_institution_id
     OR NEW.to_institution_id IS DISTINCT FROM OLD.to_institution_id
     OR NEW.title IS DISTINCT FROM OLD.title
     OR NEW.proposed_by_actor_id IS DISTINCT FROM OLD.proposed_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CONTRACT GUARD: contract identity fields are immutable';
  END IF;
  IF OLD.status <> 'proposed' AND NEW.terms_json IS DISTINCT FROM OLD.terms_json THEN
    RAISE EXCEPTION 'CONTRACT GUARD: terms are frozen after acceptance';
  END IF;
  IF OLD.status IN ('fulfilled','breached','terminated') THEN
    RAISE EXCEPTION 'CONTRACT GUARD: % contract is terminal', OLD.status;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status THEN
    IF NOT ((OLD.status = 'proposed' AND NEW.status IN ('accepted','terminated'))
         OR (OLD.status = 'accepted' AND NEW.status IN ('active','terminated'))
         OR (OLD.status = 'active' AND NEW.status IN ('fulfilled','breached','terminated'))) THEN
      RAISE EXCEPTION 'CONTRACT GUARD: illegal contract transition % -> %', OLD.status, NEW.status;
    END IF;
    IF NEW.status IN ('fulfilled','breached','terminated') AND NEW.closed_at IS NULL THEN
      RAISE EXCEPTION 'CONTRACT GUARD: terminal contract transition requires closed_at';
    END IF;
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_inter_institution_contract_guard ON inter_institution_contracts;
CREATE TRIGGER trg_inter_institution_contract_guard
  BEFORE UPDATE ON inter_institution_contracts
  FOR EACH ROW EXECUTE FUNCTION inter_institution_contract_guard();

-- Append-only histories and no deletes.
DROP TRIGGER IF EXISTS trg_society_transitions_append_only ON society_state_transitions;
CREATE TRIGGER trg_society_transitions_append_only
  BEFORE UPDATE ON society_state_transitions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c3_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C3 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'societies','society_state_transitions','society_charters','society_jurisdictions',
    'society_memberships','institution_society_memberships','institution_jurisdiction_grants',
    'institution_charters','institution_mandates','institution_powers','institution_limits',
    'inter_institution_contracts'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c3_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON society_state_transitions FROM PUBLIC;
REVOKE DELETE ON societies, society_charters, society_jurisdictions, society_memberships FROM PUBLIC;
REVOKE DELETE ON institution_society_memberships, institution_jurisdiction_grants FROM PUBLIC;
REVOKE DELETE ON institution_charters, institution_mandates, institution_powers, institution_limits FROM PUBLIC;
REVOKE DELETE ON inter_institution_contracts FROM PUBLIC;
