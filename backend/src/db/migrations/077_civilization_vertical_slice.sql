-- Migration 077: Civilization vertical slice verification support.
--
-- These tables do not implement a demo subsystem. They persist the runtime trace,
-- Postgres-backed vector index, coordinator tick, and generality metric produced
-- by the canonical civilization e2e verifier.

CREATE TABLE IF NOT EXISTS civilization_vertical_slice_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  correlation_id UUID NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('running', 'passed', 'failed')),
  runtime_mode TEXT NOT NULL,
  llm_model TEXT,
  embedding_model TEXT,
  stage_results JSONB NOT NULL DEFAULT '{}'::jsonb,
  runtime_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
  failure_reason TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_civ_vertical_slice_status ON civilization_vertical_slice_runs(status);
CREATE INDEX IF NOT EXISTS idx_civ_vertical_slice_started ON civilization_vertical_slice_runs(started_at DESC);

CREATE TABLE IF NOT EXISTS civilization_vector_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES civilization_vertical_slice_runs(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_dimensions INT NOT NULL CHECK (embedding_dimensions > 0),
  embedding_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (run_id, source_id)
);

CREATE TABLE IF NOT EXISTS civilization_vector_index (
  run_id UUID NOT NULL REFERENCES civilization_vertical_slice_runs(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES civilization_vector_documents(id) ON DELETE CASCADE,
  dimension INT NOT NULL CHECK (dimension >= 0),
  value DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (document_id, dimension)
);

CREATE INDEX IF NOT EXISTS idx_civ_vector_index_dimension_value
  ON civilization_vector_index (dimension, value);
CREATE INDEX IF NOT EXISTS idx_civ_vector_index_run_dimension
  ON civilization_vector_index (run_id, dimension);

CREATE TABLE IF NOT EXISTS civilization_generality_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES civilization_vertical_slice_runs(id) ON DELETE CASCADE,
  metric_name TEXT NOT NULL,
  domain TEXT NOT NULL,
  score DOUBLE PRECISION NOT NULL CHECK (score BETWEEN 0 AND 1),
  evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_civ_generality_run ON civilization_generality_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_civ_generality_metric ON civilization_generality_metrics(metric_name, domain);

CREATE TABLE IF NOT EXISTS civilization_coordinator_ticks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES civilization_vertical_slice_runs(id) ON DELETE CASCADE,
  tick_type TEXT NOT NULL,
  trace_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_civ_coordinator_ticks_run ON civilization_coordinator_ticks(run_id);
