ALTER TABLE eval_suites
  ADD COLUMN IF NOT EXISTS eval_type TEXT NOT NULL DEFAULT 'safety',
  ADD COLUMN IF NOT EXISTS total_cases INTEGER NOT NULL DEFAULT 0;

ALTER TABLE eval_runs
  ADD COLUMN IF NOT EXISTS total_cases INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS run_status TEXT;

UPDATE eval_runs
SET started_at = COALESCE(started_at, run_timestamp),
    run_status = COALESCE(run_status, status);

ALTER TABLE eval_scorecards
  ADD COLUMN IF NOT EXISTS overall_score DOUBLE PRECISION;

