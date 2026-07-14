-- Migration 138: Learning and safe evolution (build phase C10).
--
-- The civilization-level safe-evolution loop that connects failures to
-- improvements: observed -> candidate -> analysed -> test_generated ->
-- sandboxed -> evaluated -> approved -> canary -> promoted | rejected ->
-- monitored -> retained | rolled_back. Independent evaluation is enforced
-- (evaluator actor <> proposer actor). Canary and rollback are executable and
-- recorded. This connects existing learner/candidate/skill machinery into one
-- governed lifecycle; it does not replace them.

CREATE TABLE IF NOT EXISTS civ_learning_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  source TEXT NOT NULL
    CHECK (source IN ('resolved_prediction','task_failure','benchmark','audit','dispute',
                      'user_feedback','near_miss','safety_incident','resource_inefficiency','calibration_regression')),
  learning_form TEXT NOT NULL
    CHECK (learning_form IN ('skill','tool','prompt','policy','routing','planning',
                             'memory_policy','calibration_threshold','institution_process')),
  title TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  proposer_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  tier INTEGER NOT NULL DEFAULT 2 CHECK (tier BETWEEN 1 AND 3),
  source_mission_id UUID REFERENCES missions(id),
  status TEXT NOT NULL DEFAULT 'observed'
    CHECK (status IN ('observed','candidate','analysed','test_generated','sandboxed','evaluated',
                      'approved','rejected','canary','promoted','monitored','retained','rolled_back')),
  reject_reason TEXT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_civ_learning_candidates_status ON civ_learning_candidates (civilization_id, status);

CREATE TABLE IF NOT EXISTS civ_candidate_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS civ_failure_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  failure_summary TEXT NOT NULL,
  root_cause TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  analysed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (candidate_id)
);

CREATE TABLE IF NOT EXISTS civ_regression_cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  case_key TEXT NOT NULL,
  case_kind TEXT NOT NULL CHECK (case_kind IN ('metric_floor','safety_invariant','held_out','calibration_non_regression')),
  spec_json JSONB NOT NULL,
  held_out BOOLEAN NOT NULL DEFAULT false,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, case_key)
);

CREATE TABLE IF NOT EXISTS civ_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  evaluator_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  passed BOOLEAN NOT NULL,
  cases_total INTEGER NOT NULL,
  cases_passed INTEGER NOT NULL,
  safety_non_regression BOOLEAN NOT NULL,
  calibration_non_regression BOOLEAN NOT NULL,
  evidence_non_regression BOOLEAN NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (candidate_id)
);

CREATE TABLE IF NOT EXISTS civ_canary_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running','clean','breached')),
  metric_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  breach_reason TEXT,
  run_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  ended_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_civ_canary_candidate ON civ_canary_runs (candidate_id);

CREATE TABLE IF NOT EXISTS civ_improvement_lineage (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES civ_learning_candidates(id) ON DELETE RESTRICT,
  version INTEGER NOT NULL,
  artifact_hash TEXT NOT NULL,
  previous_version INTEGER,
  decision TEXT NOT NULL CHECK (decision IN ('promoted','rolled_back')),
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION civ_candidate_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('retained','rolled_back','rejected') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'SAFE-EVOLUTION GUARD: % candidate is terminal', OLD.status;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.safe_evolution_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'SAFE-EVOLUTION GUARD: candidate status may only change through the safe-evolution service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.proposer_actor_id IS DISTINCT FROM OLD.proposer_actor_id
     OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'SAFE-EVOLUTION GUARD: candidate identity fields are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_candidate_guard ON civ_learning_candidates;
CREATE TRIGGER trg_civ_candidate_guard
  BEFORE UPDATE ON civ_learning_candidates
  FOR EACH ROW EXECUTE FUNCTION civ_candidate_guard();

DROP TRIGGER IF EXISTS trg_civ_candidate_transitions_append_only ON civ_candidate_transitions;
CREATE TRIGGER trg_civ_candidate_transitions_append_only
  BEFORE UPDATE ON civ_candidate_transitions FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_civ_improvement_lineage_append_only ON civ_improvement_lineage;
CREATE TRIGGER trg_civ_improvement_lineage_append_only
  BEFORE UPDATE ON civ_improvement_lineage FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_civ_evaluations_append_only ON civ_evaluations;
CREATE TRIGGER trg_civ_evaluations_append_only
  BEFORE UPDATE ON civ_evaluations FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c10_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C10 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'civ_learning_candidates','civ_candidate_transitions','civ_failure_analyses','civ_regression_cases',
    'civ_evaluations','civ_canary_runs','civ_improvement_lineage'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c10_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON civ_candidate_transitions, civ_improvement_lineage, civ_evaluations FROM PUBLIC;
REVOKE DELETE ON civ_learning_candidates, civ_failure_analyses, civ_regression_cases, civ_canary_runs FROM PUBLIC;
