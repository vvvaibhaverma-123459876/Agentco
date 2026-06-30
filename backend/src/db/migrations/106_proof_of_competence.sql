-- Migration 106: L6 proof of competence.
--
-- Mints durable competence proofs for registered skill versions after all
-- required regression cases pass and the aggregate score clears threshold.

CREATE TABLE IF NOT EXISTS proof_of_competence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill_version_id UUID NOT NULL REFERENCES skill_library_versions(id) ON DELETE RESTRICT,
  skill_id UUID NOT NULL REFERENCES skill_library_entries(id) ON DELETE RESTRICT,
  evaluation_label TEXT NOT NULL,
  threshold NUMERIC NOT NULL CHECK (threshold >= 0 AND threshold <= 1),
  aggregate_score NUMERIC NOT NULL CHECK (aggregate_score >= 0 AND aggregate_score <= 1),
  passed BOOLEAN NOT NULL,
  proof_hash TEXT NOT NULL UNIQUE,
  evaluation_json JSONB NOT NULL,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  minted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (skill_version_id, evaluation_label)
);

CREATE INDEX IF NOT EXISTS idx_proof_of_competence_skill
  ON proof_of_competence(skill_id, minted_at DESC);
CREATE INDEX IF NOT EXISTS idx_proof_of_competence_version
  ON proof_of_competence(skill_version_id, minted_at DESC);
CREATE INDEX IF NOT EXISTS idx_proof_of_competence_passed
  ON proof_of_competence(passed, minted_at DESC);
