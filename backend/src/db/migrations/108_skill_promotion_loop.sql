-- Migration 108: VCA skill promotion loop.
--
-- Persists closed-loop skill promotions after protected-surface validation and
-- capability expansion approval.

CREATE TABLE IF NOT EXISTS skill_promotion_loop_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_version_id UUID NOT NULL REFERENCES skill_library_versions(id) ON DELETE RESTRICT,
  capability_expansion_decision_id UUID NOT NULL REFERENCES capability_expansion_decisions(id) ON DELETE RESTRICT,
  protected_surface_result_json JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('promoted', 'blocked')),
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (skill_version_id, capability_expansion_decision_id)
);

CREATE INDEX IF NOT EXISTS idx_skill_promotion_loop_status
  ON skill_promotion_loop_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_promotion_loop_skill
  ON skill_promotion_loop_runs(skill_version_id, created_at DESC);
