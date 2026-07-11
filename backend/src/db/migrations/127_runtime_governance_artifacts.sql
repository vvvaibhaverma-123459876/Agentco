-- Migration 127: Durable runtime governance artifacts.
--
-- These tables back the Python Phase 10-12 runtime services in production:
-- evaluation records, controlled-learning artifacts, and bounded
-- self-improvement experiments. Rows are idempotent by stable id and keep
-- canonical payload fingerprints so application code can reject mutation of
-- historical governance-critical material.

CREATE TABLE IF NOT EXISTS runtime_evaluation_records (
  evaluation_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  attempt_id TEXT NOT NULL,
  evaluator_id TEXT NOT NULL,
  evaluation_version TEXT NOT NULL,
  evaluator_result TEXT NOT NULL CHECK (evaluator_result IN ('passed', 'failed')),
  failure_category TEXT NOT NULL,
  payload JSONB NOT NULL,
  fingerprint TEXT NOT NULL,
  audit_log_id UUID REFERENCES decision_log(log_id) ON DELETE RESTRICT,
  audit_backend TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_eval_attempt
  ON runtime_evaluation_records(agent_id, task_id, attempt_id, evaluator_id);
CREATE INDEX IF NOT EXISTS idx_runtime_eval_subject
  ON runtime_evaluation_records(agent_id, evaluator_result, created_at);

CREATE TABLE IF NOT EXISTS runtime_learning_artifacts (
  artifact_id TEXT PRIMARY KEY,
  artifact_version TEXT NOT NULL,
  proposer_id TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('proposed', 'evaluated', 'approved', 'canary', 'promoted', 'rejected', 'rolled_back')),
  approval_status TEXT NOT NULL,
  surface TEXT,
  previous_active_artifact_id TEXT REFERENCES runtime_learning_artifacts(artifact_id) ON DELETE RESTRICT,
  payload JSONB NOT NULL,
  immutable_fingerprint TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runtime_learning_state
  ON runtime_learning_artifacts(state, updated_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_learning_active_surface
  ON runtime_learning_artifacts(surface)
  WHERE state = 'promoted' AND surface IS NOT NULL;

CREATE TABLE IF NOT EXISTS runtime_improvement_experiments (
  experiment_id TEXT PRIMARY KEY,
  experiment_version TEXT NOT NULL,
  proposer_id TEXT NOT NULL,
  evaluator TEXT NOT NULL,
  experiment_kind TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('accepted', 'rejected', 'blocked', 'failed')),
  promotion_recommendation TEXT NOT NULL,
  payload JSONB NOT NULL,
  immutable_fingerprint TEXT NOT NULL,
  audit_log_id UUID REFERENCES decision_log(log_id) ON DELETE RESTRICT,
  audit_backend TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_runtime_experiment_outcome
  ON runtime_improvement_experiments(outcome, created_at);

CREATE OR REPLACE FUNCTION enforce_runtime_evaluation_immutable()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'runtime_evaluation_records is append-only: DELETE is forbidden';
  END IF;

  IF NEW.fingerprint <> OLD.fingerprint OR NEW.payload <> OLD.payload THEN
    RAISE EXCEPTION 'runtime_evaluation_records payload is immutable';
  END IF;

  IF OLD.audit_log_id IS NOT NULL AND NEW.audit_log_id IS DISTINCT FROM OLD.audit_log_id THEN
    RAISE EXCEPTION 'runtime_evaluation_records audit_log_id is immutable once set';
  END IF;

  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_runtime_evaluation_immutable ON runtime_evaluation_records;
CREATE TRIGGER trg_runtime_evaluation_immutable
  BEFORE UPDATE OR DELETE ON runtime_evaluation_records
  FOR EACH ROW EXECUTE FUNCTION enforce_runtime_evaluation_immutable();

CREATE OR REPLACE FUNCTION enforce_runtime_experiment_immutable()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'runtime_improvement_experiments is append-only: DELETE is forbidden';
  END IF;

  IF NEW.immutable_fingerprint <> OLD.immutable_fingerprint THEN
    RAISE EXCEPTION 'runtime_improvement_experiments immutable payload changed';
  END IF;

  IF OLD.audit_log_id IS NOT NULL AND NEW.audit_log_id IS DISTINCT FROM OLD.audit_log_id THEN
    RAISE EXCEPTION 'runtime_improvement_experiments audit_log_id is immutable once set';
  END IF;

  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_runtime_experiment_immutable ON runtime_improvement_experiments;
CREATE TRIGGER trg_runtime_experiment_immutable
  BEFORE UPDATE OR DELETE ON runtime_improvement_experiments
  FOR EACH ROW EXECUTE FUNCTION enforce_runtime_experiment_immutable();

CREATE OR REPLACE FUNCTION enforce_runtime_learning_fingerprint()
RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'runtime_learning_artifacts cannot be deleted';
  END IF;

  IF NEW.immutable_fingerprint <> OLD.immutable_fingerprint THEN
    RAISE EXCEPTION 'runtime_learning_artifacts immutable payload changed';
  END IF;

  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_runtime_learning_fingerprint ON runtime_learning_artifacts;
CREATE TRIGGER trg_runtime_learning_fingerprint
  BEFORE UPDATE OR DELETE ON runtime_learning_artifacts
  FOR EACH ROW EXECUTE FUNCTION enforce_runtime_learning_fingerprint();

REVOKE DELETE ON runtime_evaluation_records FROM PUBLIC;
REVOKE DELETE ON runtime_learning_artifacts FROM PUBLIC;
REVOKE DELETE ON runtime_improvement_experiments FROM PUBLIC;
