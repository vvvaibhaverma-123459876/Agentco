-- Migration 105: L12 skill library.
--
-- Stores versioned skill artifacts promoted from learner candidates after
-- regression coverage exists. Competence evaluation and proof minting remain
-- separate L6/L12 responsibilities.

CREATE TABLE IF NOT EXISTS skill_library_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_key TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'retired')),
  current_version_id UUID,
  created_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS skill_library_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_id UUID NOT NULL REFERENCES skill_library_entries(id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  candidate_id UUID NOT NULL REFERENCES learner_candidates(id) ON DELETE RESTRICT,
  learner_run_id UUID NOT NULL REFERENCES learner_runs(id) ON DELETE RESTRICT,
  artifact_id UUID NOT NULL REFERENCES artifacts(id) ON DELETE RESTRICT,
  artifact_hash TEXT NOT NULL,
  contract_json JSONB NOT NULL,
  regression_test_ids UUID[] NOT NULL DEFAULT '{}',
  metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  simulation_trained BOOLEAN NOT NULL,
  status TEXT NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'active', 'retired')),
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (skill_id, version),
  UNIQUE (candidate_id)
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'fk_skill_library_current_version'
       AND conrelid = 'skill_library_entries'::regclass
  ) THEN
    ALTER TABLE skill_library_entries
      ADD CONSTRAINT fk_skill_library_current_version
      FOREIGN KEY (current_version_id)
      REFERENCES skill_library_versions(id)
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_skill_library_entries_status
  ON skill_library_entries(status);
CREATE INDEX IF NOT EXISTS idx_skill_library_versions_skill
  ON skill_library_versions(skill_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_library_versions_candidate
  ON skill_library_versions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_skill_library_versions_artifact_hash
  ON skill_library_versions(artifact_hash);
