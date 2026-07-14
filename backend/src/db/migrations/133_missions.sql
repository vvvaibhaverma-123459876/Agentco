-- Migration 133: Objectives, goals, missions, and work hierarchy (build phase C5).
--
-- Hierarchy: civilization_objective -> strategic_goal -> mission -> workstream
--            -> task -> action. Missions carry an evidence bundle, an outcome,
-- and a final attestation. Mission completion is gated: it cannot reach
-- 'completed' while required workstreams, evidence, settlement, or audit remain
-- incomplete (enforced in the service; the terminal transition also records the
-- attestation). Mission dependencies are acyclic (runtime check + self-edge CHECK).
--
-- Mission tasks/actions reference the canonical durable-task path (workflow_tasks)
-- rather than duplicating a task engine.

CREATE TABLE IF NOT EXISTS strategic_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  objective_id UUID REFERENCES civilization_objectives(id),
  society_id UUID REFERENCES societies(id),
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','active','achieved','abandoned')),
  priority INTEGER NOT NULL DEFAULT 100,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_strategic_goals_status ON strategic_goals (civilization_id, status);

CREATE TABLE IF NOT EXISTS missions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  strategic_goal_id UUID REFERENCES strategic_goals(id),
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  origin TEXT NOT NULL DEFAULT 'internal' CHECK (origin IN ('internal','external')),
  submitted_by TEXT,
  lead_institution_id VARCHAR REFERENCES institutions(id),
  coalition_id UUID REFERENCES institution_coalitions(id),
  risk_level TEXT NOT NULL DEFAULT 'low' CHECK (risk_level IN ('low','medium','high','critical')),
  requires_review BOOLEAN NOT NULL DEFAULT false,
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','triaged','approved','funded','planned','assigned','executing',
                      'waiting_for_evidence','waiting_for_review','blocked','evaluating',
                      'completed','failed','cancelled','escalated','settled','archived')),
  block_reason TEXT,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (civilization_id, status);

CREATE TABLE IF NOT EXISTS mission_dependencies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  depends_on_mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (mission_id <> depends_on_mission_id),
  UNIQUE (mission_id, depends_on_mission_id)
);

CREATE TABLE IF NOT EXISTS mission_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workstreams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  assigned_institution_id VARCHAR REFERENCES institutions(id),
  required BOOLEAN NOT NULL DEFAULT true,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','executing','completed','failed','cancelled')),
  saga_id UUID REFERENCES saga_executions(id),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_workstreams_mission ON workstreams (mission_id, status);

CREATE TABLE IF NOT EXISTS mission_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workstream_id UUID NOT NULL REFERENCES workstreams(id) ON DELETE RESTRICT,
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  -- Optional link to the canonical durable task; SET NULL so the pre-existing
  -- workflow_tasks lifecycle (and its test cleanup) is never blocked.
  workflow_task_id UUID REFERENCES workflow_tasks(task_id) ON DELETE SET NULL,
  title TEXT NOT NULL,
  agent_id TEXT,
  task_type TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','running','completed','failed','blocked')),
  attempts INTEGER NOT NULL DEFAULT 0,
  reversible BOOLEAN NOT NULL DEFAULT false,
  compensated BOOLEAN NOT NULL DEFAULT false,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_mission_tasks_mission ON mission_tasks (mission_id, status);

CREATE TABLE IF NOT EXISTS mission_action_attempts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_task_id UUID NOT NULL REFERENCES mission_tasks(id) ON DELETE RESTRICT,
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  attempt_number INTEGER NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('succeeded','failed','compensated')),
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mission_evidence_bundle (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  -- Join table over the pre-existing (deletable) autonomy_evidence. CASCADE so
  -- evidence lifecycle is never blocked; the mission attestation snapshots the
  -- evidence_ids at completion, preserving the durable record independently.
  evidence_id UUID NOT NULL REFERENCES autonomy_evidence(id) ON DELETE CASCADE,
  linked_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mission_id, evidence_id)
);

CREATE TABLE IF NOT EXISTS mission_outcomes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  result TEXT NOT NULL CHECK (result IN ('success','partial','failure')),
  summary TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mission_id)
);

CREATE TABLE IF NOT EXISTS mission_settlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  settlement_json JSONB NOT NULL,
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mission_id)
);

CREATE TABLE IF NOT EXISTS mission_attestations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  mission_id UUID NOT NULL REFERENCES missions(id) ON DELETE RESTRICT,
  attestation_json JSONB NOT NULL,
  attestation_hash TEXT NOT NULL,
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (mission_id)
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION mission_status_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('archived') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'MISSION GUARD: archived mission % is immutable', OLD.id;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.mission_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'MISSION GUARD: status may only change through the mission service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'MISSION GUARD: identity columns are immutable';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mission_status_guard ON missions;
CREATE TRIGGER trg_mission_status_guard
  BEFORE UPDATE ON missions
  FOR EACH ROW EXECUTE FUNCTION mission_status_guard();

DROP TRIGGER IF EXISTS trg_mission_transitions_append_only ON mission_state_transitions;
CREATE TRIGGER trg_mission_transitions_append_only
  BEFORE UPDATE ON mission_state_transitions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_mission_attempts_append_only ON mission_action_attempts;
CREATE TRIGGER trg_mission_attempts_append_only
  BEFORE UPDATE ON mission_action_attempts
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_mission_outcomes_append_only ON mission_outcomes;
CREATE TRIGGER trg_mission_outcomes_append_only
  BEFORE UPDATE ON mission_outcomes
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_mission_settlements_append_only ON mission_settlements;
CREATE TRIGGER trg_mission_settlements_append_only
  BEFORE UPDATE ON mission_settlements
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_mission_attestations_append_only ON mission_attestations;
CREATE TRIGGER trg_mission_attestations_append_only
  BEFORE UPDATE ON mission_attestations
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c5_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C5 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  -- mission_evidence_bundle intentionally omitted: it is a join table over the
  -- deletable autonomy_evidence with ON DELETE CASCADE (see column comment).
  FOREACH t IN ARRAY ARRAY[
    'strategic_goals','missions','mission_dependencies','mission_state_transitions','workstreams',
    'mission_tasks','mission_action_attempts','mission_outcomes',
    'mission_settlements','mission_attestations'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c5_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON mission_state_transitions, mission_action_attempts,
  mission_outcomes, mission_settlements, mission_attestations FROM PUBLIC;
REVOKE DELETE ON strategic_goals, missions, mission_dependencies, workstreams,
  mission_tasks, mission_evidence_bundle FROM PUBLIC;
