-- Migration 111: self-improvement loop persistence.
--
-- Completes the candidate lifecycle beyond registration:
--   candidate_evaluations : deterministic evaluation of ready_for_eval
--                           candidates against their generated regression
--                           cases plus measured benchmark deltas
--   skill_canary_runs     : bounded canary executions comparing baseline vs
--                           candidate strategy before any promotion
--   longitudinal_learning_cycles : durable record of full observe ->
--                           propose -> evaluate -> canary -> promote/rollback
--                           -> reuse cycles with before/after metrics

CREATE TABLE IF NOT EXISTS candidate_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES learner_candidates(id) ON DELETE RESTRICT,
  evaluation_mode TEXT NOT NULL DEFAULT 'deterministic'
    CHECK (evaluation_mode IN ('deterministic', 'live')),
  baseline_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  candidate_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  case_results_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  improvement_delta DOUBLE PRECISION,
  passed BOOLEAN NOT NULL,
  failure_reason TEXT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_candidate_evaluations_candidate
  ON candidate_evaluations(candidate_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_candidate_evaluations_passed
  ON candidate_evaluations(passed, created_at DESC);

CREATE TABLE IF NOT EXISTS skill_canary_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  candidate_id UUID NOT NULL REFERENCES learner_candidates(id) ON DELETE RESTRICT,
  evaluation_id UUID REFERENCES candidate_evaluations(id) ON DELETE RESTRICT,
  task_family TEXT NOT NULL,
  strategy TEXT NOT NULL,
  risk_tier TEXT NOT NULL DEFAULT 'low'
    CHECK (risk_tier IN ('low', 'medium', 'high', 'critical')),
  max_iterations INTEGER NOT NULL,
  iterations_used INTEGER NOT NULL,
  baseline_score DOUBLE PRECISION NOT NULL,
  canary_score DOUBLE PRECISION NOT NULL,
  improvement DOUBLE PRECISION NOT NULL,
  passed BOOLEAN NOT NULL,
  status TEXT NOT NULL DEFAULT 'completed'
    CHECK (status IN ('completed', 'aborted')),
  usage_log_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_skill_canary_runs_candidate
  ON skill_canary_runs(candidate_id, created_at DESC);

CREATE TABLE IF NOT EXISTS longitudinal_learning_cycles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cycle_label TEXT NOT NULL,
  task_family TEXT NOT NULL,
  domain TEXT NOT NULL,
  candidate_id UUID REFERENCES learner_candidates(id) ON DELETE RESTRICT,
  evaluation_id UUID REFERENCES candidate_evaluations(id) ON DELETE RESTRICT,
  canary_run_id UUID REFERENCES skill_canary_runs(id) ON DELETE RESTRICT,
  skill_version_id UUID REFERENCES skill_library_versions(id) ON DELETE RESTRICT,
  baseline_score DOUBLE PRECISION NOT NULL,
  improved_score DOUBLE PRECISION,
  score_delta DOUBLE PRECISION,
  outcome TEXT NOT NULL
    CHECK (outcome IN ('improved', 'rolled_back', 'no_change')),
  lineage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_longitudinal_cycles_label
  ON longitudinal_learning_cycles(cycle_label, created_at DESC);
