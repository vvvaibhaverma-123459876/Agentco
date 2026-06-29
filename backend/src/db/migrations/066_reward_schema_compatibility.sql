-- Compatibility bridge between the legacy reward schema from 025_goal_management_clean
-- and the newer reward services that track domain/versioned reward functions.

ALTER TABLE reward_functions
  ADD COLUMN IF NOT EXISTS domain TEXT NOT NULL DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS version TEXT NOT NULL DEFAULT '1.0',
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

ALTER TABLE reward_calculations
  ADD COLUMN IF NOT EXISTS reward_function_id UUID REFERENCES reward_functions(id),
  ADD COLUMN IF NOT EXISTS reward_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS components_json JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE reward_calculations
SET reward_function_id = COALESCE(reward_function_id, function_id),
    reward_score = COALESCE(reward_score, reward_value),
    components_json = CASE
      WHEN components_json = '{}'::jsonb AND metrics_json IS NOT NULL THEN metrics_json
      ELSE components_json
    END;

