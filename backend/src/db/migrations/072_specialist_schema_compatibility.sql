ALTER TABLE autonomy_team_activations
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE autonomy_evidence
  ADD COLUMN IF NOT EXISTS goal_id UUID;

ALTER TABLE autonomy_claims
  ADD COLUMN IF NOT EXISTS goal_id UUID;

