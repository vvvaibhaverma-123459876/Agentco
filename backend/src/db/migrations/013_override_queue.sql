-- Human Override Queue: persists every high/critical action that requires human
-- approval before execution. The BLOCKING INVARIANT: an action may not execute
-- until status='approved'. No timeout-auto-approve path exists.
CREATE TABLE IF NOT EXISTS override_queue (
    request_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id            VARCHAR(64) NOT NULL,
    action              VARCHAR(256) NOT NULL,
    risk_score          DECIMAL(4,3) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    risk_level          VARCHAR(16) NOT NULL CHECK (risk_level IN ('high','critical')),
    context             JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sla_hours           DECIMAL(6,2) NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,
    status              VARCHAR(16) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','approved','rejected','expired')),
    resolved_by         VARCHAR(128),
    resolved_at         TIMESTAMPTZ,
    resolution_notes    TEXT,
    approval_token      UUID,           -- set on approval; callers verify this token
    blocked_action_hash TEXT            -- SHA-256 of the blocked payload (for audit)
);

-- Prevent update of immutable fields after creation
CREATE OR REPLACE FUNCTION enforce_override_immutability() RETURNS TRIGGER AS $$
BEGIN
    -- These fields can never change after insert
    IF NEW.agent_id   IS DISTINCT FROM OLD.agent_id   OR
       NEW.action     IS DISTINCT FROM OLD.action     OR
       NEW.risk_level IS DISTINCT FROM OLD.risk_level OR
       NEW.created_at IS DISTINCT FROM OLD.created_at
    THEN
        RAISE EXCEPTION 'override_queue immutability violation: agent_id/action/risk_level/created_at are immutable';
    END IF;
    -- Once resolved (not pending), status cannot change again
    IF OLD.status != 'pending' THEN
        RAISE EXCEPTION 'override_queue write-once violation: request % is already %', OLD.request_id, OLD.status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER override_immutability
    BEFORE UPDATE ON override_queue
    FOR EACH ROW EXECUTE FUNCTION enforce_override_immutability();

-- No physical deletes — overrides are a permanent record
REVOKE DELETE ON override_queue FROM PUBLIC;

CREATE INDEX idx_override_queue_status    ON override_queue(status);
CREATE INDEX idx_override_queue_agent     ON override_queue(agent_id);
CREATE INDEX idx_override_queue_expires   ON override_queue(expires_at) WHERE status='pending';
CREATE INDEX idx_override_queue_created   ON override_queue(created_at DESC);
