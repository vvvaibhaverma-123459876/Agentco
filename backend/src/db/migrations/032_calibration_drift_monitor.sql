-- Migration 032: Calibration Drift Monitor
--
-- Monitors calibration quality in real-world conditions and detects drift.
-- Proposes changes when drift exceeds thresholds (but doesn't apply them).
-- Can activate emergency freeze for critical drift.

-- ============================================================
-- DRIFT EVENT TYPES
-- ============================================================

DROP TYPE IF EXISTS drift_type CASCADE;
CREATE TYPE drift_type AS ENUM (
    'overconfidence',
    'underconfidence',
    'resolution_delay',
    'evidence_quality_decline',
    'reputation_drift',
    'dispute_rate_increase',
    'simulation_leakage_risk',
    'eval_failure_rate_increase',
    'rollback_rate_increase',
    'safety_threshold_violation'
);

DROP TYPE IF EXISTS drift_severity CASCADE;
CREATE TYPE drift_severity AS ENUM (
    'normal', 'warning', 'severe', 'critical'
);

-- ============================================================
-- CALIBRATION DRIFT EVENTS TABLE
-- ============================================================

DROP TABLE IF EXISTS calibration_drift_events CASCADE;
CREATE TABLE calibration_drift_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drift_type drift_type NOT NULL,
    severity drift_severity NOT NULL,
    baseline_value FLOAT NOT NULL,
    observed_value FLOAT NOT NULL,
    drift_magnitude FLOAT NOT NULL,
    threshold_value FLOAT NOT NULL,
    detection_method TEXT NOT NULL,
    affected_entity_type TEXT,
    affected_entity_id TEXT,
    proposed_change_id UUID REFERENCES calibration_change_requests(id),
    triggered_emergency_freeze BOOLEAN DEFAULT false,
    evidence_json JSONB DEFAULT '{}'::jsonb,
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_drift_events_type ON calibration_drift_events(drift_type);
CREATE INDEX idx_drift_events_severity ON calibration_drift_events(severity);
CREATE INDEX idx_drift_events_created_at ON calibration_drift_events(created_at DESC);
CREATE INDEX idx_drift_events_resolved ON calibration_drift_events(resolved_at);

-- ============================================================
-- DRIFT THRESHOLDS TABLE
-- ============================================================

DROP TABLE IF EXISTS drift_thresholds CASCADE;
CREATE TABLE drift_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drift_type drift_type NOT NULL UNIQUE,
    warning_threshold FLOAT NOT NULL,
    severe_threshold FLOAT NOT NULL,
    critical_threshold FLOAT NOT NULL,
    requires_emergency_freeze BOOLEAN DEFAULT false,
    auto_propose_change BOOLEAN DEFAULT true,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_thresholds_type ON drift_thresholds(drift_type);

-- ============================================================
-- DRIFT RESOLUTION TABLE
-- ============================================================

DROP TABLE IF EXISTS drift_resolutions CASCADE;
CREATE TABLE drift_resolutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    drift_event_id UUID NOT NULL REFERENCES calibration_drift_events(id),
    resolution_type TEXT NOT NULL,
    resolution_change_id UUID REFERENCES calibration_change_requests(id),
    resolution_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_by_entity_id TEXT,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_resolutions_drift ON drift_resolutions(drift_event_id);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS drift_events_immutable_resolved ON calibration_drift_events;
CREATE TRIGGER drift_events_immutable_resolved
    BEFORE UPDATE ON calibration_drift_events
    FOR EACH ROW
    WHEN (OLD.resolved_at IS NOT NULL)
    EXECUTE FUNCTION raise_immutability_violation('calibration_drift_events resolved');

DROP TRIGGER IF EXISTS drift_resolutions_immutable ON drift_resolutions;
CREATE TRIGGER drift_resolutions_immutable
    BEFORE UPDATE ON drift_resolutions
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('drift_resolutions');

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION calculate_drift_magnitude(
    p_baseline FLOAT,
    p_observed FLOAT
)
RETURNS FLOAT AS $$
BEGIN
    IF p_baseline = 0 THEN
        RETURN ABS(p_observed);
    END IF;
    RETURN ABS((p_observed - p_baseline) / p_baseline);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_drift_severity(
    p_drift_magnitude FLOAT,
    p_warning_threshold FLOAT,
    p_severe_threshold FLOAT,
    p_critical_threshold FLOAT
)
RETURNS drift_severity AS $$
BEGIN
    IF p_drift_magnitude >= p_critical_threshold THEN
        RETURN 'critical'::drift_severity;
    ELSIF p_drift_magnitude >= p_severe_threshold THEN
        RETURN 'severe'::drift_severity;
    ELSIF p_drift_magnitude >= p_warning_threshold THEN
        RETURN 'warning'::drift_severity;
    ELSE
        RETURN 'normal'::drift_severity;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_active_unresolved_critical_drift_count()
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM calibration_drift_events
        WHERE severity = 'critical'::drift_severity
        AND resolved_at IS NULL
        AND created_at > NOW() - INTERVAL '1 hour'
    );
END;
$$ LANGUAGE plpgsql;
