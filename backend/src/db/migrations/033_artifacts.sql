-- Migration 029: Simple artifacts table
--
-- Unified table for storing learning-generated artifacts (prompts, configs, etc)

CREATE TABLE IF NOT EXISTS artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'prompt_update',
        'config_update',
        'heuristic_update',
        'memory_policy_update'
    )),
    artifact_hash TEXT NOT NULL UNIQUE,
    artifact_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    lineage_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_simulation_derived BOOLEAN NOT NULL DEFAULT false,
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN (
        'created',
        'tested',
        'promoted',
        'deployed',
        'archived'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_type ON artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_hash ON artifacts(artifact_hash);
CREATE INDEX IF NOT EXISTS idx_artifacts_status ON artifacts(status);
CREATE INDEX IF NOT EXISTS idx_artifacts_created_at ON artifacts(created_at);
