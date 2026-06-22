-- Migration 029: Rollback Infrastructure for Canary Deployments
--
-- Provides the schema for capturing pre-deployment state, tracking active artifacts,
-- and recording rollback events for canary deployment safety.
--
-- These tables are required by:
-- - backend/src/services/rollback.service.ts
-- - Phases 9-13 canary/rollback workflow
-- - Civilization calibration trust-policy rollout

-- ============================================================
-- DEPLOYMENT SNAPSHOTS: Pre-deployment state capture
-- ============================================================

CREATE TABLE IF NOT EXISTS deployment_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id UUID,
    artifact_id_active UUID NOT NULL,
    artifact_id_previous UUID,
    policy_version TEXT,
    baseline_metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_deployment_snapshots_canary_plan ON deployment_snapshots(canary_plan_id);
CREATE INDEX IF NOT EXISTS idx_deployment_snapshots_created_at ON deployment_snapshots(created_at);


-- ============================================================
-- ACTIVE ARTIFACTS: Track current live artifact per type/scope
-- ============================================================

CREATE TABLE IF NOT EXISTS active_artifacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_type TEXT NOT NULL,
    scope_level TEXT,
    scope_entity_id UUID,
    artifact_id UUID NOT NULL,
    previous_artifact_id UUID,
    version INT DEFAULT 1,
    activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    replaced_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(artifact_type, scope_level, scope_entity_id)
);

CREATE INDEX IF NOT EXISTS idx_active_artifacts_artifact_type ON active_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_active_artifacts_artifact_id ON active_artifacts(artifact_id);
CREATE INDEX IF NOT EXISTS idx_active_artifacts_activated_at ON active_artifacts(activated_at);


-- ============================================================
-- CANARY ROLLBACK EVENTS: Immutable rollback audit trail
-- ============================================================

CREATE TABLE IF NOT EXISTS canary_rollback_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canary_plan_id UUID NOT NULL,
    artifact_id_rolled_back_from UUID NOT NULL,
    artifact_id_rolled_back_to UUID NOT NULL,
    reason TEXT NOT NULL,
    triggered_by TEXT NOT NULL,
    previous_metrics_json JSONB DEFAULT '{}'::jsonb,
    rollback_metrics_json JSONB DEFAULT '{}'::jsonb,
    success BOOLEAN NOT NULL DEFAULT false,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_canary_plan ON canary_rollback_events(canary_plan_id);
CREATE INDEX IF NOT EXISTS idx_canary_rollback_events_created_at ON canary_rollback_events(created_at);


-- ============================================================
-- IMMUTABILITY: Rollback events cannot be modified after creation
-- ============================================================

CREATE TRIGGER canary_rollback_events_immutable
    BEFORE UPDATE ON canary_rollback_events
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('canary_rollback_events');
