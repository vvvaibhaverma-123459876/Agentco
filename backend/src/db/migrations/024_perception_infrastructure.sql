-- Migration 024: Perception adapter infrastructure
--
-- Perception sources, events, and artifacts. All external environment
-- data goes through adapter → normalization → artifact storage.

CREATE TABLE IF NOT EXISTS perception_sources (
    id TEXT PRIMARY KEY,
    source_type TEXT NOT NULL CHECK (source_type IN (
        'local_file',
        'http_readonly',
        'postgres',
        'simulator',
        'kafka_stream',
        'custom'
    )),
    name TEXT NOT NULL,
    description TEXT,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    permissions_json JSONB NOT NULL DEFAULT '{
        "allowlist": [],
        "rate_limit_per_minute": 60,
        "max_content_size_mb": 100,
        "allowed_mime_types": []
    }'::jsonb,
    active BOOLEAN NOT NULL DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_perception_sources_source_type ON perception_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_perception_sources_active ON perception_sources(active);


-- Normalized perception events
CREATE TABLE IF NOT EXISTS perception_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES perception_sources(id),
    event_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_fingerprint TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    provenance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id TEXT,
    task_id UUID REFERENCES autonomy_tasks(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_perception_events_source_id ON perception_events(source_id);
CREATE INDEX IF NOT EXISTS idx_perception_events_source_fingerprint ON perception_events(source_fingerprint);
CREATE INDEX IF NOT EXISTS idx_perception_events_task_id ON perception_events(task_id);
CREATE INDEX IF NOT EXISTS idx_perception_events_created_at ON perception_events(created_at);


-- Artifact storage for perception data
CREATE TABLE IF NOT EXISTS perception_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES perception_events(id),
    artifact_type TEXT NOT NULL CHECK (artifact_type IN (
        'file_content',
        'http_response',
        'db_record',
        'structured_data',
        'media',
        'custom'
    )),
    artifact_hash TEXT NOT NULL UNIQUE,
    storage_uri TEXT NOT NULL,
    content_size_bytes BIGINT,
    mime_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_perception_artifacts_event_id ON perception_artifacts(event_id);
CREATE INDEX IF NOT EXISTS idx_perception_artifacts_artifact_hash ON perception_artifacts(artifact_hash);
CREATE INDEX IF NOT EXISTS idx_perception_artifacts_artifact_type ON perception_artifacts(artifact_type);


-- Adapter run history for debugging
CREATE TABLE IF NOT EXISTS perception_adapter_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id TEXT NOT NULL REFERENCES perception_sources(id),
    adapter_version TEXT,
    status TEXT NOT NULL CHECK (status IN ('success', 'partial_success', 'failure')),
    events_fetched INT NOT NULL DEFAULT 0,
    artifacts_stored INT NOT NULL DEFAULT 0,
    error_message TEXT,
    duration_ms BIGINT,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_perception_adapter_runs_source_id ON perception_adapter_runs(source_id);
CREATE INDEX IF NOT EXISTS idx_perception_adapter_runs_status ON perception_adapter_runs(status);
CREATE INDEX IF NOT EXISTS idx_perception_adapter_runs_created_at ON perception_adapter_runs(created_at);


-- Immutable: perception events and artifacts
DROP TRIGGER IF EXISTS perception_events_immutable_after_created ON perception_events;
CREATE TRIGGER perception_events_immutable_after_created
    BEFORE UPDATE ON perception_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('perception_events');

DROP TRIGGER IF EXISTS perception_artifacts_immutable_after_created ON perception_artifacts;
CREATE TRIGGER perception_artifacts_immutable_after_created
    BEFORE UPDATE ON perception_artifacts
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('perception_artifacts');
