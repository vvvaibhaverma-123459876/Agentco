-- Migration 130: Citizenry (build phase C2).
--
-- Citizens are actor-backed members of the civilization. Citizenship status
-- gates protected execution; roles are institution/time scoped; autonomy
-- envelopes are domain scoped; sanctions require external authorization;
-- succession transfers responsibilities without transferring identity.
--
-- Guard pattern follows migration 129: CHECK lifecycles, partial unique
-- indexes, append-only triggers, and a SET LOCAL service gate for status
-- transitions.

CREATE TABLE IF NOT EXISTS citizens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL UNIQUE REFERENCES actors(id) ON DELETE RESTRICT,
  citizen_type TEXT NOT NULL CHECK (citizen_type IN ('agent','human','service')),
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK (status IN ('candidate','probationary','active','restricted','suspended','expelled','retired')),
  display_name TEXT NOT NULL,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_citizens_status ON citizens (civilization_id, status);

CREATE TABLE IF NOT EXISTS citizenship_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  changed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  sanction_id UUID,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_citizenship_records_citizen
  ON citizenship_records (citizen_id, created_at DESC);

CREATE TABLE IF NOT EXISTS citizen_sanctions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  sanction_type TEXT NOT NULL
    CHECK (sanction_type IN ('warning','restriction','suspension','expulsion','budget_penalty')),
  reason TEXT NOT NULL,
  imposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  authorized_decision_ref TEXT NOT NULL,
  effective_until TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','lifted','expired')),
  lifted_by_actor_id UUID REFERENCES actors(id),
  lifted_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_citizen_sanctions_citizen
  ON citizen_sanctions (citizen_id, status);

ALTER TABLE citizenship_records
  DROP CONSTRAINT IF EXISTS citizenship_records_sanction_fk;
ALTER TABLE citizenship_records
  ADD CONSTRAINT citizenship_records_sanction_fk
  FOREIGN KEY (sanction_id) REFERENCES citizen_sanctions(id);

CREATE TABLE IF NOT EXISTS citizen_role_eligibility (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  role_name TEXT NOT NULL,
  -- institutions.id is VARCHAR in the legacy schema; match it exactly.
  institution_id VARCHAR REFERENCES institutions(id),
  domain TEXT,
  valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
  valid_to TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (valid_to IS NULL OR valid_to > valid_from)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_citizen_role_eligibility_active
  ON citizen_role_eligibility (
    citizen_id, role_name,
    COALESCE(institution_id, ''),
    COALESCE(domain, '')
  ) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS citizen_autonomy_envelopes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  domain TEXT NOT NULL,
  max_risk_level TEXT NOT NULL CHECK (max_risk_level IN ('low','medium','high','critical')),
  budget_multiplier NUMERIC NOT NULL DEFAULT 1.0 CHECK (budget_multiplier > 0 AND budget_multiplier <= 10),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_citizen_envelope_active
  ON citizen_autonomy_envelopes (citizen_id, domain) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS citizen_successions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  from_citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  to_citizen_id UUID NOT NULL REFERENCES citizens(id) ON DELETE RESTRICT,
  transferred_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
  scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  reason TEXT NOT NULL,
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (from_citizen_id <> to_citizen_id)
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION citizenship_status_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('expelled','retired') THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: % citizen % is immutable', OLD.status, OLD.id;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.citizenship_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: status may only change through the citizenship service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.actor_id IS DISTINCT FROM OLD.actor_id
     OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.citizen_type IS DISTINCT FROM OLD.citizen_type
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: identity columns are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizenship_status_guard ON citizens;
CREATE TRIGGER trg_citizenship_status_guard
  BEFORE UPDATE ON citizens
  FOR EACH ROW EXECUTE FUNCTION citizenship_status_guard();

CREATE OR REPLACE FUNCTION citizenship_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'CITIZENSHIP GUARD: % rows are append-only', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizenship_records_append_only ON citizenship_records;
CREATE TRIGGER trg_citizenship_records_append_only
  BEFORE UPDATE ON citizenship_records
  FOR EACH ROW EXECUTE FUNCTION citizenship_append_only();

DROP TRIGGER IF EXISTS trg_citizen_successions_append_only ON citizen_successions;
CREATE TRIGGER trg_citizen_successions_append_only
  BEFORE UPDATE ON citizen_successions
  FOR EACH ROW EXECUTE FUNCTION citizenship_append_only();

-- Sanction guard: imposition fields frozen; only active→lifted|expired with
-- lift metadata.
CREATE OR REPLACE FUNCTION citizen_sanction_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.citizen_id IS DISTINCT FROM OLD.citizen_id
     OR NEW.sanction_type IS DISTINCT FROM OLD.sanction_type
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.imposed_by_actor_id IS DISTINCT FROM OLD.imposed_by_actor_id
     OR NEW.authorized_decision_ref IS DISTINCT FROM OLD.authorized_decision_ref
     OR NEW.effective_until IS DISTINCT FROM OLD.effective_until
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: sanction imposition fields are immutable';
  END IF;
  IF NOT (OLD.status = 'active' AND NEW.status IN ('lifted','expired')) THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: illegal sanction status transition % -> %', OLD.status, NEW.status;
  END IF;
  IF NEW.lifted_at IS NULL THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: sanction termination requires lifted_at';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizen_sanction_guard ON citizen_sanctions;
CREATE TRIGGER trg_citizen_sanction_guard
  BEFORE UPDATE ON citizen_sanctions
  FOR EACH ROW EXECUTE FUNCTION citizen_sanction_guard();

-- Eligibility/envelope guard: grant fields frozen; only active→revoked with
-- revocation metadata.
CREATE OR REPLACE FUNCTION citizen_grant_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.citizen_id IS DISTINCT FROM OLD.citizen_id
     OR NEW.granted_by_actor_id IS DISTINCT FROM OLD.granted_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: grant fields are immutable';
  END IF;
  IF NOT (OLD.status = 'active' AND NEW.status = 'revoked') THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: illegal grant status transition % -> %', OLD.status, NEW.status;
  END IF;
  IF NEW.revoked_at IS NULL THEN
    RAISE EXCEPTION 'CITIZENSHIP GUARD: revocation requires revoked_at';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizen_role_grant_guard ON citizen_role_eligibility;
CREATE TRIGGER trg_citizen_role_grant_guard
  BEFORE UPDATE ON citizen_role_eligibility
  FOR EACH ROW EXECUTE FUNCTION citizen_grant_guard();

DROP TRIGGER IF EXISTS trg_citizen_envelope_grant_guard ON citizen_autonomy_envelopes;
CREATE TRIGGER trg_citizen_envelope_grant_guard
  BEFORE UPDATE ON citizen_autonomy_envelopes
  FOR EACH ROW EXECUTE FUNCTION citizen_grant_guard();

CREATE OR REPLACE FUNCTION citizenship_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'CITIZENSHIP GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_citizens_no_delete ON citizens;
CREATE TRIGGER trg_citizens_no_delete
  BEFORE DELETE ON citizens FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();
DROP TRIGGER IF EXISTS trg_citizenship_records_no_delete ON citizenship_records;
CREATE TRIGGER trg_citizenship_records_no_delete
  BEFORE DELETE ON citizenship_records FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();
DROP TRIGGER IF EXISTS trg_citizen_sanctions_no_delete ON citizen_sanctions;
CREATE TRIGGER trg_citizen_sanctions_no_delete
  BEFORE DELETE ON citizen_sanctions FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();
DROP TRIGGER IF EXISTS trg_citizen_role_eligibility_no_delete ON citizen_role_eligibility;
CREATE TRIGGER trg_citizen_role_eligibility_no_delete
  BEFORE DELETE ON citizen_role_eligibility FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();
DROP TRIGGER IF EXISTS trg_citizen_envelopes_no_delete ON citizen_autonomy_envelopes;
CREATE TRIGGER trg_citizen_envelopes_no_delete
  BEFORE DELETE ON citizen_autonomy_envelopes FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();
DROP TRIGGER IF EXISTS trg_citizen_successions_no_delete ON citizen_successions;
CREATE TRIGGER trg_citizen_successions_no_delete
  BEFORE DELETE ON citizen_successions FOR EACH ROW EXECUTE FUNCTION citizenship_no_delete();

REVOKE UPDATE, DELETE ON citizenship_records FROM PUBLIC;
REVOKE UPDATE, DELETE ON citizen_successions FROM PUBLIC;
REVOKE DELETE ON citizens FROM PUBLIC;
REVOKE DELETE ON citizen_sanctions FROM PUBLIC;
REVOKE DELETE ON citizen_role_eligibility FROM PUBLIC;
REVOKE DELETE ON citizen_autonomy_envelopes FROM PUBLIC;
