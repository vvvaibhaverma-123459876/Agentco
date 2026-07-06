-- Migration 121: Repair runtime schema drift caught by full-system tests.
-- Purpose: make already-migrated databases match the runtime contract that
-- earlier compatibility migrations intended to provide.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'risk_level') THEN
    CREATE TYPE risk_level AS ENUM ('low', 'medium', 'high', 'critical');
  END IF;
END $$;

ALTER TABLE learner_candidates
  ADD COLUMN IF NOT EXISTS risk_level risk_level NOT NULL DEFAULT 'low',
  ADD COLUMN IF NOT EXISTS simulation_trained BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS artifact_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE autonomy_goals
  ADD COLUMN IF NOT EXISTS depth INTEGER NOT NULL DEFAULT 0;

UPDATE autonomy_goals
SET depth = COALESCE(goal_depth, depth, 0)
WHERE depth IS DISTINCT FROM COALESCE(goal_depth, depth, 0);

CREATE INDEX IF NOT EXISTS idx_autonomy_goals_depth ON autonomy_goals(depth);

DO $$
BEGIN
  ALTER TABLE autonomy_goals
    ADD CONSTRAINT depth_limit CHECK (depth <= 2);
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;
