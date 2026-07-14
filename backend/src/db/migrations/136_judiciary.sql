-- Migration 136: Judiciary completion (build phase C8).
--
-- The civilization-wide judiciary: cases move opened -> jurisdiction_check ->
-- evidence_collection -> hearing -> ruling -> enforcement -> appeal -> final ->
-- closed. Enforcement orders mutate real runtime state (resource penalties via
-- the treasury, citizen sanctions, trust adjustments). Appeals route to a
-- distinct authorized panel; duplicate final rulings are blocked; precedents
-- are searchable; dissent is retained.
--
-- The existing contradiction-specific `disputes`/`rulings` tables remain the
-- L11 claim-contradiction path; a judiciary_case can reference a source
-- dispute when a contradiction is escalated. This completes one judiciary; it
-- does not fork a second dispute runtime.

CREATE TABLE IF NOT EXISTS judiciary_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  dispute_type TEXT NOT NULL
    CHECK (dispute_type IN ('evidence_conflict','claim_challenge','prediction_resolution_challenge',
                            'resource_dispute','jurisdiction_conflict','citizen_misconduct','trust_appeal',
                            'policy_conflict','memory_retraction','capability_revocation','contract_breach')),
  title TEXT NOT NULL,
  complainant_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  respondent_scope_type TEXT NOT NULL CHECK (respondent_scope_type IN ('citizen','institution','coalition','mission','actor')),
  respondent_scope_id TEXT NOT NULL,
  source_dispute_id TEXT,
  status TEXT NOT NULL DEFAULT 'opened'
    CHECK (status IN ('opened','jurisdiction_check','evidence_collection','hearing','ruling',
                      'enforcement','appeal','final','closed','dismissed')),
  assigned_institution_id VARCHAR REFERENCES institutions(id),
  body_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_judiciary_cases_status ON judiciary_cases (civilization_id, status);

CREATE TABLE IF NOT EXISTS judiciary_case_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS judiciary_evidence_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  submitted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  evidence_id UUID REFERENCES autonomy_evidence(id) ON DELETE SET NULL,
  statement TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS judiciary_hearings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  presiding_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  summary TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'held' CHECK (status IN ('held')),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS judiciary_rulings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  ruling_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  outcome TEXT NOT NULL CHECK (outcome IN ('upheld','dismissed','partial','escalated')),
  rationale TEXT NOT NULL,
  is_precedent BOOLEAN NOT NULL DEFAULT false,
  principle TEXT,
  signature TEXT NOT NULL,
  is_appellate BOOLEAN NOT NULL DEFAULT false,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_judiciary_rulings_case ON judiciary_rulings (case_id);
-- At most one non-appellate (trial) ruling and one appellate ruling per case.
CREATE UNIQUE INDEX IF NOT EXISTS uq_judiciary_trial_ruling ON judiciary_rulings (case_id) WHERE is_appellate = false;
CREATE UNIQUE INDEX IF NOT EXISTS uq_judiciary_appellate_ruling ON judiciary_rulings (case_id) WHERE is_appellate = true;

CREATE TABLE IF NOT EXISTS judiciary_enforcement_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  ruling_id UUID NOT NULL REFERENCES judiciary_rulings(id) ON DELETE RESTRICT,
  order_type TEXT NOT NULL
    CHECK (order_type IN ('resource_penalty','citizen_sanction','trust_adjustment','capability_revocation','policy_clarification','no_action')),
  target_scope_type TEXT NOT NULL,
  target_scope_id TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'issued' CHECK (status IN ('issued','applied','reversed')),
  applied_ref TEXT,
  issued_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS judiciary_appeals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id UUID NOT NULL REFERENCES judiciary_cases(id) ON DELETE RESTRICT,
  ruling_id UUID NOT NULL REFERENCES judiciary_rulings(id) ON DELETE RESTRICT,
  appellant_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  grounds TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'filed' CHECK (status IN ('filed','ruled')),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (case_id)
);

CREATE TABLE IF NOT EXISTS judiciary_dissents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ruling_id UUID NOT NULL REFERENCES judiciary_rulings(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  opinion TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS judiciary_precedents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  ruling_id UUID NOT NULL REFERENCES judiciary_rulings(id) ON DELETE RESTRICT,
  dispute_type TEXT NOT NULL,
  principle TEXT NOT NULL,
  outcome TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ruling_id)
);
CREATE INDEX IF NOT EXISTS idx_judiciary_precedents_type ON judiciary_precedents (dispute_type, outcome);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION judiciary_case_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('closed','dismissed') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'JUDICIARY GUARD: % case is terminal', OLD.status;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.judiciary_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'JUDICIARY GUARD: case status may only change through the judiciary service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.dispute_type IS DISTINCT FROM OLD.dispute_type
     OR NEW.complainant_actor_id IS DISTINCT FROM OLD.complainant_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'JUDICIARY GUARD: case identity fields are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_judiciary_case_guard ON judiciary_cases;
CREATE TRIGGER trg_judiciary_case_guard
  BEFORE UPDATE ON judiciary_cases
  FOR EACH ROW EXECUTE FUNCTION judiciary_case_guard();

-- Rulings are immutable once issued.
DROP TRIGGER IF EXISTS trg_judiciary_rulings_append_only ON judiciary_rulings;
CREATE TRIGGER trg_judiciary_rulings_append_only
  BEFORE UPDATE ON judiciary_rulings FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_judiciary_transitions_append_only ON judiciary_case_transitions;
CREATE TRIGGER trg_judiciary_transitions_append_only
  BEFORE UPDATE ON judiciary_case_transitions FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_judiciary_dissents_append_only ON judiciary_dissents;
CREATE TRIGGER trg_judiciary_dissents_append_only
  BEFORE UPDATE ON judiciary_dissents FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_judiciary_precedents_append_only ON judiciary_precedents;
CREATE TRIGGER trg_judiciary_precedents_append_only
  BEFORE UPDATE ON judiciary_precedents FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c8_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C8 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'judiciary_cases','judiciary_case_transitions','judiciary_evidence_submissions','judiciary_hearings',
    'judiciary_rulings','judiciary_enforcement_orders','judiciary_appeals','judiciary_dissents','judiciary_precedents'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c8_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON judiciary_rulings, judiciary_case_transitions, judiciary_dissents, judiciary_precedents FROM PUBLIC;
REVOKE DELETE ON judiciary_cases, judiciary_evidence_submissions, judiciary_hearings,
  judiciary_enforcement_orders, judiciary_appeals FROM PUBLIC;
