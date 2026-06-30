-- Migration 104: L12 regression test generator.
--
-- Stores deterministic regression test cases derived from learner candidates.

CREATE TABLE IF NOT EXISTS candidate_regression_tests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES learner_candidates(id) ON DELETE CASCADE,
  learner_run_id UUID NOT NULL REFERENCES learner_runs(id) ON DELETE CASCADE,
  case_name TEXT NOT NULL,
  test_type TEXT NOT NULL CHECK (test_type IN (
    'metric_floor',
    'artifact_integrity',
    'simulation_guard'
  )),
  assertion_json JSONB NOT NULL,
  source_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  artifact_hash TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (candidate_id, case_name)
);

CREATE INDEX IF NOT EXISTS idx_candidate_regression_tests_candidate
  ON candidate_regression_tests(candidate_id);
CREATE INDEX IF NOT EXISTS idx_candidate_regression_tests_run
  ON candidate_regression_tests(learner_run_id);
CREATE INDEX IF NOT EXISTS idx_candidate_regression_tests_type
  ON candidate_regression_tests(test_type);
