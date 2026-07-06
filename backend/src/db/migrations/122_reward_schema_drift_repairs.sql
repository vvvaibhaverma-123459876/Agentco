-- Migration 122: Repair reward function compatibility drift.
-- Migration 066 defines these columns, but already-migrated local databases can
-- miss them when schema_migrations and physical schema diverge.

ALTER TABLE reward_functions
  ADD COLUMN IF NOT EXISTS domain TEXT NOT NULL DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS version TEXT NOT NULL DEFAULT '1.0.0',
  ADD COLUMN IF NOT EXISTS formula_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS owner TEXT NOT NULL DEFAULT 'system',
  ADD COLUMN IF NOT EXISTS risk_level risk_level NOT NULL DEFAULT 'low',
  ADD COLUMN IF NOT EXISTS created_by TEXT NOT NULL DEFAULT 'system';

UPDATE reward_functions
SET formula_json = parameters
WHERE formula_json = '{}'::jsonb
  AND parameters IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_reward_functions_name_version
  ON reward_functions(name, version);
