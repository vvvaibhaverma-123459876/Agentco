-- Migration 123: Repair reward calculation compatibility drift.
-- Supports both legacy inserts (function_id/reward_value) and newer reward
-- service inserts (reward_function_id/reward_score/regret_score/details).

ALTER TABLE reward_calculations
  ADD COLUMN IF NOT EXISTS reward_function_id UUID REFERENCES reward_functions(id),
  ADD COLUMN IF NOT EXISTS reward_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS regret_score DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS components_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS calculation_details_json JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE reward_calculations
SET reward_function_id = COALESCE(reward_function_id, function_id),
    reward_score = COALESCE(reward_score, reward_value),
    components_json = CASE
      WHEN components_json = '{}'::jsonb AND metrics_json IS NOT NULL THEN metrics_json
      ELSE components_json
    END,
    calculation_details_json = CASE
      WHEN calculation_details_json = '{}'::jsonb AND metrics_json IS NOT NULL THEN metrics_json
      ELSE calculation_details_json
    END;

CREATE OR REPLACE FUNCTION reward_calculations_compat_defaults()
RETURNS TRIGGER AS $$
BEGIN
  NEW.reward_function_id := COALESCE(NEW.reward_function_id, NEW.function_id);
  NEW.function_id := COALESCE(NEW.function_id, NEW.reward_function_id);
  NEW.reward_score := COALESCE(NEW.reward_score, NEW.reward_value);
  NEW.reward_value := COALESCE(NEW.reward_value, NEW.reward_score);
  NEW.metrics_json := COALESCE(NEW.metrics_json, '{}'::jsonb);
  NEW.components_json := COALESCE(NULLIF(NEW.components_json, '{}'::jsonb), NEW.metrics_json, '{}'::jsonb);
  NEW.calculation_details_json := COALESCE(
    NULLIF(NEW.calculation_details_json, '{}'::jsonb),
    NEW.components_json,
    NEW.metrics_json,
    '{}'::jsonb
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS reward_calculations_compat_defaults_trigger ON reward_calculations;
CREATE TRIGGER reward_calculations_compat_defaults_trigger
  BEFORE INSERT OR UPDATE ON reward_calculations
  FOR EACH ROW
  EXECUTE FUNCTION reward_calculations_compat_defaults();

CREATE INDEX IF NOT EXISTS idx_reward_calculations_reward_function_id
  ON reward_calculations(reward_function_id);
