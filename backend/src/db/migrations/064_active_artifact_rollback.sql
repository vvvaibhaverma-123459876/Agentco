-- Migration 064: Active artifact deployment pointers and rollback audit
--
-- Minimal active schema for backend/src/services/rollback.service.ts.
-- This records artifact pointer changes and rollback events against the deployed
-- artifacts table. It does not deploy code or modify source files.

CREATE TABLE IF NOT EXISTS deployment_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id TEXT NOT NULL,
    artifact_id_active UUID NOT NULL REFERENCES artifacts(id),
    artifact_id_previous UUID NOT NULL REFERENCES artifacts(id),
    policy_version TEXT NOT NULL DEFAULT '1.0',
    baseline_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deployment_snapshots_canary_plan ON deployment_snapshots(canary_plan_id);
CREATE INDEX IF NOT EXISTS idx_deployment_snapshots_created_at ON deployment_snapshots(created_at);

CREATE TABLE IF NOT EXISTS active_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_type TEXT NOT NULL UNIQUE,
    artifact_id UUID NOT NULL REFERENCES artifacts(id),
    previous_artifact_id UUID REFERENCES artifacts(id),
    deployed_by TEXT NOT NULL DEFAULT 'rollback_service',
    deployment_count INT NOT NULL DEFAULT 0 CHECK (deployment_count >= 0),
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_active_artifacts_artifact_type ON active_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_active_artifacts_artifact_id ON active_artifacts(artifact_id);
CREATE INDEX IF NOT EXISTS idx_active_artifacts_deployed_at ON active_artifacts(deployed_at);

CREATE TABLE IF NOT EXISTS canary_rollback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id TEXT NOT NULL,
    deployment_snapshot_id UUID NOT NULL REFERENCES deployment_snapshots(id),
    artifact_id_rolled_back_from UUID NOT NULL REFERENCES artifacts(id),
    artifact_id_rolled_back_to UUID NOT NULL REFERENCES artifacts(id),
    reason TEXT NOT NULL,
    triggered_by TEXT NOT NULL,
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pre_rollback_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    post_rollback_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_canary_plan ON canary_rollback_events(canary_plan_id);
CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_created_at ON canary_rollback_events(created_at);
CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_from ON canary_rollback_events(artifact_id_rolled_back_from);
CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_to ON canary_rollback_events(artifact_id_rolled_back_to);

DROP TRIGGER IF EXISTS canary_rollback_events_immutable ON canary_rollback_events;
CREATE TRIGGER canary_rollback_events_immutable
    BEFORE UPDATE ON canary_rollback_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('canary_rollback_events');
