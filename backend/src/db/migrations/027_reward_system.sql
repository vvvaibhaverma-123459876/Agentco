-- Migration 027: Reward functions and calculation system
--
-- Integrates with existing calibration resolution. Tracks reward
-- versions, calculations, and audit trail. Multi-dimensional rewards.

CREATE TABLE IF NOT EXISTS reward_functions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    version TEXT NOT NULL,
    formula_json JSONB NOT NULL,
    formula_description TEXT,
    owner TEXT NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    active BOOLEAN NOT NULL DEFAULT true,
    requires_approval BOOLEAN NOT NULL DEFAULT false,
    created_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(name, version)
);

CREATE INDEX IF NOT EXISTS idx_reward_functions_domain ON reward_functions(domain);
CREATE INDEX IF NOT EXISTS idx_reward_functions_active ON reward_functions(active);
CREATE INDEX IF NOT EXISTS idx_reward_functions_risk_level ON reward_functions(risk_level);


-- Reward calculations for specific outcomes
CREATE TABLE IF NOT EXISTS reward_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    outcome_id UUID NOT NULL REFERENCES autonomy_outcomes(id),
    reward_function_id UUID NOT NULL REFERENCES reward_functions(id),
    reward_score FLOAT NOT NULL,
    regret_score FLOAT,
    calculation_details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    components_json JSONB NOT NULL DEFAULT '{
        "completion": 0.0,
        "correctness": 0.0,
        "calibration": 0.0,
        "safety": 0.0,
        "cost": 0.0,
        "time": 0.0,
        "intervention": 0.0,
        "downstream_impact": 0.0
    }'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reward_calculations_outcome_id ON reward_calculations(outcome_id);
CREATE INDEX IF NOT EXISTS idx_reward_calculations_reward_function_id ON reward_calculations(reward_function_id);
CREATE INDEX IF NOT EXISTS idx_reward_calculations_created_at ON reward_calculations(created_at);


-- Audit of reward calculation changes
CREATE TABLE IF NOT EXISTS reward_audit (
    id BIGSERIAL PRIMARY KEY,
    reward_calculation_id UUID NOT NULL REFERENCES reward_calculations(id),
    reviewer_id TEXT,
    decision TEXT NOT NULL CHECK (decision IN ('accepted', 'rejected', 'needs_revision')),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reward_audit_reward_calculation_id ON reward_audit(reward_calculation_id);
CREATE INDEX IF NOT EXISTS idx_reward_audit_reviewer_id ON reward_audit(reviewer_id);


-- Enforce reward function versioning
CREATE OR REPLACE FUNCTION enforce_reward_function_versioning()
RETURNS TRIGGER AS $$
BEGIN
    -- Cannot update active reward function - must create new version
    IF OLD.active = true AND NEW.active = true THEN
        RAISE EXCEPTION 'Cannot update active reward function. Create new version instead.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER reward_functions_enforce_versioning
    BEFORE UPDATE ON reward_functions
    FOR EACH ROW
    EXECUTE FUNCTION enforce_reward_function_versioning();


-- Immutable: calculations cannot be modified
CREATE TRIGGER reward_calculations_immutable_after_created
    BEFORE UPDATE ON reward_calculations
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('reward_calculations');
