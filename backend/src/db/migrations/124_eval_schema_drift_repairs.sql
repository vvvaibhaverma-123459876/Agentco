-- Migration 124: Repair evaluation schema compatibility drift.
-- Keeps the legacy eval tables usable by both the autonomy orchestrator smoke
-- path and the newer eval harness service.

ALTER TABLE eval_suites
  ADD COLUMN IF NOT EXISTS eval_type TEXT NOT NULL DEFAULT 'safety',
  ADD COLUMN IF NOT EXISTS total_cases INTEGER NOT NULL DEFAULT 0;

ALTER TABLE eval_runs
  ADD COLUMN IF NOT EXISTS total_cases INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS target_type TEXT,
  ADD COLUMN IF NOT EXISTS target_id UUID,
  ADD COLUMN IF NOT EXISTS run_status TEXT,
  ADD COLUMN IF NOT EXISTS baseline_ref TEXT,
  ADD COLUMN IF NOT EXISTS candidate_ref TEXT,
  ADD COLUMN IF NOT EXISTS trace_id TEXT;

UPDATE eval_runs
SET started_at = COALESCE(started_at, run_timestamp),
    run_status = COALESCE(run_status, status);

ALTER TABLE eval_runs
  ALTER COLUMN run_timestamp SET DEFAULT now();

ALTER TABLE eval_scorecards
  ADD COLUMN IF NOT EXISTS overall_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS decision_reason TEXT;

UPDATE eval_scorecards
SET overall_score = COALESCE(
  overall_score,
  (COALESCE(autonomy_score, 0) + COALESCE(safety_score, 0) + COALESCE(calibration_score, 0)
   + COALESCE(planning_score, 0) + COALESCE(memory_score, 0) + COALESCE(tool_score, 0)
   + COALESCE(reward_score, 0) + COALESCE(regression_score, 0)) / 8.0
);
