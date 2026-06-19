-- Customer data: accessible only to CX, Sales, and Legal agents — NOT Marketing or Engineering
CREATE TABLE IF NOT EXISTS customer_data (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         VARCHAR(64) NOT NULL UNIQUE,
    company_name        VARCHAR(256),
    arr                 DECIMAL(12,2) NOT NULL DEFAULT 0,
    health_score        INTEGER NOT NULL DEFAULT 100 CHECK (health_score BETWEEN 0 AND 100),
    contract_start      DATE,
    contract_end        DATE,
    plan                VARCHAR(64),
    primary_contact_id  VARCHAR(64),
    last_interaction_at TIMESTAMPTZ,
    risk_factors        JSONB DEFAULT '[]',
    tags                TEXT[] DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Row-level security: enforce access control at DB level
ALTER TABLE customer_data ENABLE ROW LEVEL SECURITY;

-- Only CX, Sales, Legal agents may read customer PII
-- (agent_id injected via session variable set by the API layer)
DROP POLICY IF EXISTS customer_data_access ON customer_data;
CREATE POLICY customer_data_access ON customer_data
    USING (
        current_setting('app.agent_id', true) IN (
            'support-agent','success-agent','voice-agent',
            'sdr-agent','ae-agent','revops-agent',
            'contract-agent','risk-agent','privacy-agent',
            'ceo-agent','cfo-agent','coo-agent'
        )
    );

CREATE INDEX IF NOT EXISTS idx_customer_health ON customer_data(health_score);
CREATE INDEX IF NOT EXISTS idx_customer_arr ON customer_data(arr);
CREATE INDEX IF NOT EXISTS idx_customer_contract_end ON customer_data(contract_end);
