-- Migration 031: Trust Reputation Ledger
--
-- Implements event-sourced reputation tracking for entities across all 5 levels.
-- Reputation is built from immutable events, never directly modified.
-- Separate reputation tracks for real-world and simulation contexts.

-- ============================================================
-- REPUTATION EVENT TYPES
-- ============================================================

DROP TYPE IF EXISTS reputation_event_type CASCADE;
CREATE TYPE reputation_event_type AS ENUM (
    'accurate_prediction',
    'failed_prediction',
    'overconfident_claim',
    'underconfident_correct',
    'unsafe_action_blocked',
    'dispute_resolution_quality',
    'calibration_improvement',
    'calibration_regression',
    'rollback_triggered',
    'protected_surface_violation',
    'governance_review_quality',
    'memory_quality_improvement',
    'memory_quality_decline',
    'evidence_quality_good',
    'evidence_quality_poor',
    'correction_event'
);

DROP TYPE IF EXISTS reputation_context CASCADE;
CREATE TYPE reputation_context AS ENUM (
    'real_world',
    'simulation',
    'both'
);

-- ============================================================
-- TRUST REPUTATION LEDGER TABLE
-- ============================================================

DROP TABLE IF EXISTS trust_reputation_ledger CASCADE;
CREATE TABLE trust_reputation_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type reputation_event_type NOT NULL,
    context reputation_context NOT NULL DEFAULT 'real_world',
    impact_value FLOAT NOT NULL,
    impact_confidence FLOAT NOT NULL,
    source_ref UUID,
    source_type TEXT,
    evidence_json JSONB DEFAULT '{}'::jsonb,
    corrects_event_id UUID REFERENCES trust_reputation_ledger(id),
    trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reputation_entity ON trust_reputation_ledger(entity_type, entity_id);
CREATE INDEX idx_reputation_event_type ON trust_reputation_ledger(event_type);
CREATE INDEX idx_reputation_context ON trust_reputation_ledger(context);
CREATE INDEX idx_reputation_created_at ON trust_reputation_ledger(created_at);
CREATE INDEX idx_reputation_correction ON trust_reputation_ledger(corrects_event_id);

-- ============================================================
-- REPUTATION SNAPSHOTS TABLE
-- ============================================================

DROP TABLE IF EXISTS reputation_snapshots CASCADE;
CREATE TABLE reputation_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    context reputation_context NOT NULL,
    reputation_score FLOAT NOT NULL,
    event_count INT NOT NULL,
    positive_events INT NOT NULL,
    negative_events INT NOT NULL,
    confidence FLOAT NOT NULL,
    snapshot_timestamp TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_snapshots_entity ON reputation_snapshots(entity_type, entity_id);
CREATE INDEX idx_snapshots_context ON reputation_snapshots(context);
CREATE INDEX idx_snapshots_timestamp ON reputation_snapshots(snapshot_timestamp DESC);

-- ============================================================
-- REPUTATION IMPACT WEIGHTS TABLE
-- ============================================================

DROP TABLE IF EXISTS reputation_impact_weights CASCADE;
CREATE TABLE reputation_impact_weights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type reputation_event_type NOT NULL UNIQUE,
    base_weight FLOAT NOT NULL,
    context reputation_context NOT NULL DEFAULT 'both',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_weights_event_type ON reputation_impact_weights(event_type);

-- ============================================================
-- IMMUTABILITY TRIGGERS
-- ============================================================

DROP TRIGGER IF EXISTS reputation_ledger_immutable ON trust_reputation_ledger;
CREATE TRIGGER reputation_ledger_immutable
    BEFORE UPDATE ON trust_reputation_ledger
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('trust_reputation_ledger');

DROP TRIGGER IF EXISTS reputation_snapshots_immutable ON reputation_snapshots;
CREATE TRIGGER reputation_snapshots_immutable
    BEFORE UPDATE ON reputation_snapshots
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('reputation_snapshots');

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION get_entity_reputation(
    p_entity_type TEXT,
    p_entity_id TEXT,
    p_context reputation_context DEFAULT 'real_world'
)
RETURNS FLOAT AS $$
DECLARE
    v_total_weight FLOAT := 0.0;
    v_total_impact FLOAT := 0.0;
    v_weight FLOAT;
    v_impact FLOAT;
BEGIN
    FOR v_impact, v_weight IN
        SELECT trl.impact_value, riw.base_weight
        FROM trust_reputation_ledger trl
        LEFT JOIN reputation_impact_weights riw ON riw.event_type = trl.event_type
        WHERE trl.entity_type = p_entity_type
        AND trl.entity_id = p_entity_id
        AND (trl.context = p_context OR trl.context = 'both'::reputation_context)
        AND trl.corrects_event_id IS NULL
        ORDER BY trl.created_at DESC
    LOOP
        v_weight := COALESCE(v_weight, 1.0);
        v_total_impact := v_total_impact + (v_impact * v_weight);
        v_total_weight := v_total_weight + v_weight;
    END LOOP;

    IF v_total_weight = 0 THEN
        RETURN 0.5;
    END IF;

    RETURN LEAST(1.0, GREATEST(0.0, (v_total_impact / v_total_weight + 1.0) / 2.0));
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_reputation_event_count(
    p_entity_type TEXT,
    p_entity_id TEXT,
    p_context reputation_context DEFAULT 'real_world'
)
RETURNS INT AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM trust_reputation_ledger
        WHERE entity_type = p_entity_type
        AND entity_id = p_entity_id
        AND (context = p_context OR context = 'both'::reputation_context)
        AND corrects_event_id IS NULL
    );
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_reputation_snapshot(
    p_entity_type TEXT,
    p_entity_id TEXT,
    p_context reputation_context
)
RETURNS UUID AS $$
DECLARE
    v_snapshot_id UUID;
    v_reputation FLOAT;
    v_event_count INT;
    v_positive INT;
    v_negative INT;
BEGIN
    v_reputation := get_entity_reputation(p_entity_type, p_entity_id, p_context);
    v_event_count := get_reputation_event_count(p_entity_type, p_entity_id, p_context);

    v_positive := (
        SELECT COUNT(*)
        FROM trust_reputation_ledger
        WHERE entity_type = p_entity_type
        AND entity_id = p_entity_id
        AND (context = p_context OR context = 'both'::reputation_context)
        AND impact_value > 0.0
        AND corrects_event_id IS NULL
    );

    v_negative := v_event_count - v_positive;

    INSERT INTO reputation_snapshots (
        entity_type, entity_id, context, reputation_score,
        event_count, positive_events, negative_events,
        confidence, snapshot_timestamp
    ) VALUES (
        p_entity_type, p_entity_id, p_context, v_reputation,
        v_event_count, v_positive, v_negative,
        GREATEST(0.5, 1.0 - (1.0 / (v_event_count + 1.0))), NOW()
    )
    RETURNING id INTO v_snapshot_id;

    RETURN v_snapshot_id;
END;
$$ LANGUAGE plpgsql;
