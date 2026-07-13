-- Migration 129: Civilization kernel (build phase C1).
--
-- The civilization root aggregate: lifecycle, append-only versions and
-- charters, jurisdictions, tier-0 protected invariants, auto-expiring
-- emergency states, and civilization objectives. All scoped civilization
-- objects added by later phases reference civilizations(id).
--
-- Guards follow the repo's established pattern: CHECK constraints for
-- lifecycle values, partial unique indexes for singletons, REVOKE plus
-- BEFORE-trigger enforcement (REVOKE alone is insufficient because the table
-- owner bypasses it — see migration 014), and a SET LOCAL authorization gate
-- so status changes can only happen through the kernel service (mirrors the
-- civilization reputation guard).

CREATE TABLE IF NOT EXISTS civilizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'forming'
    CHECK (status IN ('forming','active','restricted','emergency','recovering','suspended','retired')),
  description TEXT NOT NULL DEFAULT '',
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Exactly one active civilization root for the canonical runtime.
CREATE UNIQUE INDEX IF NOT EXISTS uq_civilizations_single_active
  ON civilizations ((1)) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS civilization_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  content_json JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, version_number)
);

CREATE TABLE IF NOT EXISTS civilization_charters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  version_number INTEGER NOT NULL CHECK (version_number >= 1),
  charter_json JSONB NOT NULL,
  charter_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','active','superseded')),
  activated_at TIMESTAMPTZ,
  activated_by_actor_id UUID REFERENCES actors(id),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, version_number)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_civilization_charter_single_active
  ON civilization_charters (civilization_id) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS civilization_jurisdictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  jurisdiction_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','retired')),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, jurisdiction_key)
);

CREATE TABLE IF NOT EXISTS civilization_protected_invariants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  invariant_key TEXT NOT NULL,
  description TEXT NOT NULL,
  tier INTEGER NOT NULL DEFAULT 0 CHECK (tier BETWEEN 0 AND 3),
  enforcement TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, invariant_key)
);

CREATE TABLE IF NOT EXISTS civilization_emergency_states (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL,
  reason TEXT NOT NULL,
  activated_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  authorized_decision_ref TEXT NOT NULL,
  activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked')),
  ended_at TIMESTAMPTZ,
  ended_by_actor_id UUID REFERENCES actors(id),
  event_log_id UUID REFERENCES event_log(id),
  CHECK (expires_at > activated_at)
);

-- One active emergency per (civilization, scope); history preserved.
CREATE UNIQUE INDEX IF NOT EXISTS uq_civ_emergency_active_scope
  ON civilization_emergency_states (civilization_id, scope) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_civ_emergency_due
  ON civilization_emergency_states (expires_at) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS civilization_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  authorized_decision_ref TEXT,
  emergency_state_id UUID REFERENCES civilization_emergency_states(id),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_civ_transitions_civ
  ON civilization_state_transitions (civilization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS civilization_objectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','active','achieved','abandoned','superseded')),
  priority INTEGER NOT NULL DEFAULT 100,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, title)
);
CREATE INDEX IF NOT EXISTS idx_civ_objectives_status
  ON civilization_objectives (civilization_id, status, priority);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

-- Kernel status guard: retired civilizations are immutable; status changes
-- require the kernel-service transaction gate.
CREATE OR REPLACE FUNCTION civilization_kernel_status_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'retired' THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: retired civilization % is immutable', OLD.id;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.kernel_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: status may only change through the kernel service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.name IS DISTINCT FROM OLD.name
     OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: identity columns are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civilization_kernel_status_guard ON civilizations;
CREATE TRIGGER trg_civilization_kernel_status_guard
  BEFORE UPDATE ON civilizations
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_status_guard();

-- Append-only tables: reject every UPDATE.
CREATE OR REPLACE FUNCTION civilization_kernel_append_only() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: % rows are append-only', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_versions_append_only ON civilization_versions;
CREATE TRIGGER trg_civ_versions_append_only
  BEFORE UPDATE ON civilization_versions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

DROP TRIGGER IF EXISTS trg_civ_transitions_append_only ON civilization_state_transitions;
CREATE TRIGGER trg_civ_transitions_append_only
  BEFORE UPDATE ON civilization_state_transitions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

DROP TRIGGER IF EXISTS trg_civ_invariants_append_only ON civilization_protected_invariants;
CREATE TRIGGER trg_civ_invariants_append_only
  BEFORE UPDATE ON civilization_protected_invariants
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

-- Charter guard: content is frozen once written; only draft→active and
-- active→superseded status moves (with activation metadata) are allowed.
CREATE OR REPLACE FUNCTION civilization_charter_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.version_number IS DISTINCT FROM OLD.version_number
     OR NEW.charter_json IS DISTINCT FROM OLD.charter_json
     OR NEW.charter_hash IS DISTINCT FROM OLD.charter_hash
     OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: charter content is immutable';
  END IF;
  IF NOT ((OLD.status = 'draft' AND NEW.status = 'active')
       OR (OLD.status = 'active' AND NEW.status = 'superseded')
       OR (OLD.status = NEW.status)) THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: illegal charter status transition % -> %', OLD.status, NEW.status;
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_charter_guard ON civilization_charters;
CREATE TRIGGER trg_civ_charter_guard
  BEFORE UPDATE ON civilization_charters
  FOR EACH ROW EXECUTE FUNCTION civilization_charter_guard();

-- Emergency-state guard: activation fields frozen; only active→expired and
-- active→revoked terminations (with end metadata) are allowed.
CREATE OR REPLACE FUNCTION civilization_emergency_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.scope IS DISTINCT FROM OLD.scope
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.activated_by_actor_id IS DISTINCT FROM OLD.activated_by_actor_id
     OR NEW.authorized_decision_ref IS DISTINCT FROM OLD.authorized_decision_ref
     OR NEW.activated_at IS DISTINCT FROM OLD.activated_at
     OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: emergency activation fields are immutable';
  END IF;
  IF NOT (OLD.status = 'active' AND NEW.status IN ('expired','revoked')) THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: illegal emergency status transition % -> %', OLD.status, NEW.status;
  END IF;
  IF NEW.ended_at IS NULL THEN
    RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: emergency termination requires ended_at';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_emergency_guard ON civilization_emergency_states;
CREATE TRIGGER trg_civ_emergency_guard
  BEFORE UPDATE ON civilization_emergency_states
  FOR EACH ROW EXECUTE FUNCTION civilization_emergency_guard();

-- No kernel table allows DELETE.
CREATE OR REPLACE FUNCTION civilization_kernel_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'CIVILIZATION KERNEL GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civilizations_no_delete ON civilizations;
CREATE TRIGGER trg_civilizations_no_delete
  BEFORE DELETE ON civilizations
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

DROP TRIGGER IF EXISTS trg_civ_versions_no_delete ON civilization_versions;
CREATE TRIGGER trg_civ_versions_no_delete
  BEFORE DELETE ON civilization_versions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

DROP TRIGGER IF EXISTS trg_civ_charters_no_delete ON civilization_charters;
CREATE TRIGGER trg_civ_charters_no_delete
  BEFORE DELETE ON civilization_charters
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

DROP TRIGGER IF EXISTS trg_civ_transitions_no_delete ON civilization_state_transitions;
CREATE TRIGGER trg_civ_transitions_no_delete
  BEFORE DELETE ON civilization_state_transitions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

DROP TRIGGER IF EXISTS trg_civ_invariants_no_delete ON civilization_protected_invariants;
CREATE TRIGGER trg_civ_invariants_no_delete
  BEFORE DELETE ON civilization_protected_invariants
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

DROP TRIGGER IF EXISTS trg_civ_emergency_no_delete ON civilization_emergency_states;
CREATE TRIGGER trg_civ_emergency_no_delete
  BEFORE DELETE ON civilization_emergency_states
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_no_delete();

REVOKE UPDATE, DELETE ON civilization_versions FROM PUBLIC;
REVOKE UPDATE, DELETE ON civilization_state_transitions FROM PUBLIC;
REVOKE UPDATE, DELETE ON civilization_protected_invariants FROM PUBLIC;
REVOKE DELETE ON civilizations FROM PUBLIC;
REVOKE DELETE ON civilization_charters FROM PUBLIC;
REVOKE DELETE ON civilization_emergency_states FROM PUBLIC;
