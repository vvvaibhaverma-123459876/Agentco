-- Migration 103: L13 generality metric tracker.
--
-- Persists cross-domain benchmark results against registered active domains.

CREATE TABLE IF NOT EXISTS generality_metric_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  benchmark_name TEXT NOT NULL,
  mode TEXT NOT NULL,
  aggregate_score NUMERIC NOT NULL CHECK (aggregate_score >= 0 AND aggregate_score <= 1),
  baseline_score NUMERIC NOT NULL CHECK (baseline_score >= 0 AND baseline_score <= 1),
  domains_evaluated INT NOT NULL CHECK (domains_evaluated > 0),
  domains_above_baseline INT NOT NULL CHECK (domains_above_baseline >= 0),
  generality_score NUMERIC NOT NULL CHECK (generality_score >= 0 AND generality_score <= 1),
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_generality_metric_runs_benchmark
  ON generality_metric_runs(benchmark_name, created_at DESC);

CREATE TABLE IF NOT EXISTS generality_domain_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES generality_metric_runs(id) ON DELETE CASCADE,
  domain_id UUID NOT NULL REFERENCES domain_registry(id) ON DELETE RESTRICT,
  domain_key TEXT NOT NULL,
  score NUMERIC NOT NULL CHECK (score >= 0 AND score <= 1),
  baseline_score NUMERIC NOT NULL CHECK (baseline_score >= 0 AND baseline_score <= 1),
  beats_baseline BOOLEAN NOT NULL,
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, domain_id)
);

CREATE INDEX IF NOT EXISTS idx_generality_domain_scores_domain
  ON generality_domain_scores(domain_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generality_domain_scores_run
  ON generality_domain_scores(run_id);
