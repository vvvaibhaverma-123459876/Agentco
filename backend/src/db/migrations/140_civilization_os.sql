-- Migration 140: Civilization operating system (build phase C12).
--
-- The continuous coordinator's durable state: a singleton control row (mode +
-- heartbeat + tick count), an append-only tick log recording what each tick
-- sourced/routed/settled, and the civilization-wide status projection. Leader
-- election uses a Postgres advisory lock (see CivilizationOSService), so only
-- one active scheduler ticks at a time even across restarts.

CREATE TABLE IF NOT EXISTS civ_os_state (
  id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  civilization_id UUID REFERENCES civilizations(id),
  mode TEXT NOT NULL DEFAULT 'stopped' CHECK (mode IN ('stopped','running','paused','drained')),
  tick_count BIGINT NOT NULL DEFAULT 0,
  last_leader_instance TEXT,
  heartbeat_at TIMESTAMPTZ,
  updated_by_actor_id UUID REFERENCES actors(id),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS civ_os_ticks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  tick_number BIGINT NOT NULL,
  was_leader BOOLEAN NOT NULL,
  mode TEXT NOT NULL,
  work_sourced INTEGER NOT NULL DEFAULT 0,
  work_routed INTEGER NOT NULL DEFAULT 0,
  emergencies_expired INTEGER NOT NULL DEFAULT 0,
  reservations_expired INTEGER NOT NULL DEFAULT 0,
  disputes_open INTEGER NOT NULL DEFAULT 0,
  learning_candidates_open INTEGER NOT NULL DEFAULT 0,
  expansion_proposals_open INTEGER NOT NULL DEFAULT 0,
  status_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  instance TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_civ_os_ticks_number ON civ_os_ticks (tick_number DESC);

DROP TRIGGER IF EXISTS trg_civ_os_ticks_append_only ON civ_os_ticks;
CREATE TRIGGER trg_civ_os_ticks_append_only
  BEFORE UPDATE ON civ_os_ticks FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c12_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C12 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_civ_os_ticks_no_delete ON civ_os_ticks;
CREATE TRIGGER trg_civ_os_ticks_no_delete
  BEFORE DELETE ON civ_os_ticks FOR EACH ROW EXECUTE FUNCTION c12_no_delete();

REVOKE UPDATE, DELETE ON civ_os_ticks FROM PUBLIC;
