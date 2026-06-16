-- Event history: all events fired, consumed, and acknowledged on the Kafka bus
CREATE TABLE IF NOT EXISTS event_history (
    event_id            UUID PRIMARY KEY,
    event_type          VARCHAR(128) NOT NULL,
    producer_agent_id   VARCHAR(64) NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL,
    confidence_score    DECIMAL(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    payload             JSONB NOT NULL,
    correlation_id      UUID,
    risk_level          VARCHAR(16) NOT NULL
                            CHECK (risk_level IN ('low','medium','high','critical')),
    requires_ack        BOOLEAN NOT NULL DEFAULT FALSE,
    ttl_seconds         INTEGER NOT NULL DEFAULT 86400,
    acknowledged_by     TEXT[] DEFAULT '{}',
    acknowledged_at     TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

REVOKE DELETE ON event_history FROM PUBLIC;
REVOKE UPDATE ON event_history FROM PUBLIC;

CREATE INDEX idx_event_history_type ON event_history(event_type);
CREATE INDEX idx_event_history_producer ON event_history(producer_agent_id);
CREATE INDEX idx_event_history_timestamp ON event_history(timestamp DESC);
CREATE INDEX idx_event_history_correlation ON event_history(correlation_id);
CREATE INDEX idx_event_history_risk ON event_history(risk_level);
