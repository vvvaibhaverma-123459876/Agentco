-- Migration 110: skill usage events.
--
-- Closes the skill-consumption seam: every time the planner consults promoted
-- skills, the decision (used / ignored / rejected) is persisted so promoted
-- skills have an auditable influence trail instead of dead-ending as library
-- rows. Outcome fields are filled in after the action resolves.

CREATE TABLE IF NOT EXISTS skill_usage_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_version_id UUID NOT NULL REFERENCES skill_library_versions(id) ON DELETE RESTRICT,
  goal_id TEXT,
  run_id TEXT,
  agent_id TEXT,
  action_id TEXT,
  usage TEXT NOT NULL CHECK (usage IN ('used', 'ignored', 'rejected')),
  reason TEXT,
  confidence_delta DOUBLE PRECISION,
  outcome TEXT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skill_usage_events_skill
  ON skill_usage_events(skill_version_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_usage_events_goal
  ON skill_usage_events(goal_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_usage_events_usage
  ON skill_usage_events(usage, created_at DESC);
