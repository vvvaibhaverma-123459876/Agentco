-- Migration 107: L13 capability expansion gate.
--
-- Records domain expansion decisions backed by active domain registration,
-- registered skill versions, minted competence proofs, and generality metrics.

CREATE TABLE IF NOT EXISTS capability_expansion_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  domain_id UUID NOT NULL REFERENCES domain_registry(id) ON DELETE RESTRICT,
  domain_key TEXT NOT NULL,
  skill_id UUID NOT NULL REFERENCES skill_library_entries(id) ON DELETE RESTRICT,
  skill_version_id UUID NOT NULL REFERENCES skill_library_versions(id) ON DELETE RESTRICT,
  proof_id UUID NOT NULL REFERENCES proof_of_competence(id) ON DELETE RESTRICT,
  generality_run_id UUID NOT NULL REFERENCES generality_metric_runs(id) ON DELETE RESTRICT,
  baseline_score NUMERIC NOT NULL CHECK (baseline_score >= 0 AND baseline_score <= 1),
  proof_score NUMERIC NOT NULL CHECK (proof_score >= 0 AND proof_score <= 1),
  decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
  reason TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (domain_id, skill_version_id, proof_id)
);

CREATE INDEX IF NOT EXISTS idx_capability_expansion_domain
  ON capability_expansion_decisions(domain_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_capability_expansion_skill
  ON capability_expansion_decisions(skill_version_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_capability_expansion_decision
  ON capability_expansion_decisions(decision, created_at DESC);
