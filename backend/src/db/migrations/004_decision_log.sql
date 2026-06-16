-- Immutable audit log: append-only, no agent has DELETE permission
-- This is the legal and governance record of every decision in AgentCo.
CREATE TABLE IF NOT EXISTS decision_log (
    log_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id            VARCHAR(64) NOT NULL,
    action_type         VARCHAR(32) NOT NULL
                            CHECK (action_type IN ('decision','api_call','event_published','escalation')),
    input_summary       TEXT NOT NULL,
    output_summary      TEXT NOT NULL,
    confidence_score    DECIMAL(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    risk_level          VARCHAR(16) NOT NULL
                            CHECK (risk_level IN ('low','medium','high','critical')),
    human_approved      BOOLEAN NOT NULL DEFAULT FALSE,
    human_approver_id   VARCHAR(128),
    downstream_events   UUID[] DEFAULT '{}',
    session_id          UUID,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Append-only enforcement: revoke DELETE and UPDATE from all roles
REVOKE DELETE ON decision_log FROM PUBLIC;
REVOKE UPDATE ON decision_log FROM PUBLIC;

-- Indexes for audit log viewer queries
CREATE INDEX idx_decision_log_agent ON decision_log(agent_id);
CREATE INDEX idx_decision_log_timestamp ON decision_log(timestamp DESC);
CREATE INDEX idx_decision_log_risk ON decision_log(risk_level);
CREATE INDEX idx_decision_log_session ON decision_log(session_id);
CREATE INDEX idx_decision_log_human_approved ON decision_log(human_approved);
