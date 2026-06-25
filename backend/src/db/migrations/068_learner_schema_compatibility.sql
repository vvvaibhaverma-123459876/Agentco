ALTER TABLE replay_batches
  ADD COLUMN IF NOT EXISTS batch_label TEXT,
  ADD COLUMN IF NOT EXISTS simulation_derived BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS trace_id UUID;

CREATE TABLE IF NOT EXISTS replay_training_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  learner_run_id UUID NOT NULL REFERENCES learner_runs(id) ON DELETE CASCADE,
  metric_name TEXT NOT NULL,
  metric_value DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_replay_training_metrics_learner_run_id
  ON replay_training_metrics(learner_run_id);

ALTER TABLE learner_candidates
  ADD COLUMN IF NOT EXISTS artifact_ref TEXT,
  ADD COLUMN IF NOT EXISTS rationale TEXT,
  ADD COLUMN IF NOT EXISTS expected_improvement_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS risk_level risk_level NOT NULL DEFAULT 'low',
  ADD COLUMN IF NOT EXISTS simulation_trained BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS trace_id UUID,
  ADD COLUMN IF NOT EXISTS artifact_json JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE learner_candidates
  DROP CONSTRAINT IF EXISTS learner_candidates_status_check;

ALTER TABLE learner_candidates
  ADD CONSTRAINT learner_candidates_status_check
  CHECK (status IN (
    'created',
    'generated',
    'ready_for_eval',
    'evaluated',
    'promoted',
    'rejected',
    'rolled_back'
  ));

