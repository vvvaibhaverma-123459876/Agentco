ALTER TABLE reward_functions
  ALTER COLUMN function_type SET DEFAULT 'linear',
  ALTER COLUMN parameters SET DEFAULT '{}'::jsonb;

UPDATE reward_functions
SET function_type = 'linear'
WHERE function_type IS NULL;

