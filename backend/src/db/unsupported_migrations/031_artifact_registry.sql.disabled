-- Migration 031: Artifact registry and version control
--
-- All promoted artifacts (prompts, policies, models, code) are registered,
-- versioned, signed, and have lineage tracking.

CREATE TABLE IF NOT EXISTS artifact_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'prompt',
        'policy',
        'model_config',
        'planner_config',
        'memory_policy',
        'tool_policy',
        'code_patch',
        'eval_suite',
        'reward_function',
        'rule'
    )),
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    storage_uri TEXT NOT NULL,
    parent_artifact_id UUID REFERENCES artifact_registry(id),
    created_by TEXT NOT NULL,
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    signature TEXT,
    signature_algorithm TEXT,
    size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(artifact_type, name, version)
);

CREATE INDEX IF NOT EXISTS idx_artifact_registry_artifact_type ON artifact_registry(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifact_registry_hash ON artifact_registry(hash);
CREATE INDEX IF NOT EXISTS idx_artifact_registry_created_at ON artifact_registry(created_at);


-- Artifact lineage tracking
CREATE TABLE IF NOT EXISTS artifact_lineage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    parent_artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    relation_type TEXT NOT NULL CHECK (relation_type IN (
        'derived_from',
        'refined_from',
        'generated_from',
        'replaces',
        'supersedes'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_lineage_artifact_id ON artifact_lineage(artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_lineage_parent_artifact_id ON artifact_lineage(parent_artifact_id);


-- Artifact deployment tracking
CREATE TABLE IF NOT EXISTS artifact_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    environment TEXT NOT NULL CHECK (environment IN (
        'sandbox',
        'canary',
        'staging',
        'production',
        'simulation'
    )),
    deployment_status TEXT NOT NULL DEFAULT 'pending' CHECK (deployment_status IN (
        'pending',
        'in_progress',
        'successful',
        'failed',
        'rolled_back'
    )),
    canary_percentage INT CHECK (canary_percentage >= 0 AND canary_percentage <= 100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    rolled_back_at TIMESTAMPTZ,
    rollback_reason TEXT,
    metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_deployments_artifact_id ON artifact_deployments(artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_deployments_environment ON artifact_deployments(environment);
CREATE INDEX IF NOT EXISTS idx_artifact_deployments_deployment_status ON artifact_deployments(deployment_status);


-- Digital signatures
CREATE TABLE IF NOT EXISTS artifact_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id UUID NOT NULL REFERENCES artifact_registry(id),
    signer_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    signature_algorithm TEXT NOT NULL,
    public_key_ref TEXT,
    verified BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifact_signatures_artifact_id ON artifact_signatures(artifact_id);
CREATE INDEX IF NOT EXISTS idx_artifact_signatures_signer_id ON artifact_signatures(signer_id);


-- Immutable: artifacts and signatures
CREATE TRIGGER artifact_registry_immutable_after_created
    BEFORE UPDATE ON artifact_registry
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('artifact_registry');

CREATE TRIGGER artifact_signatures_immutable_after_created
    BEFORE UPDATE ON artifact_signatures
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('artifact_signatures');
