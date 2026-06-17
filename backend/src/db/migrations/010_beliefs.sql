-- Beliefs table — Reality/Simulation Firewall.
-- validation_status transitions: provisional → simulation_supported → reality_validated
-- ONLY promote_to_reality_validated() (called by ResolutionService) may set reality_validated.
-- No simulation volume can write reality_validated. Enforced by trigger.

CREATE TABLE IF NOT EXISTS beliefs (
    belief_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim              TEXT NOT NULL,
    domain             TEXT NOT NULL,
    claim_type         TEXT NOT NULL DEFAULT 'general',
    validation_status  TEXT NOT NULL DEFAULT 'provisional'
                           CHECK (validation_status IN ('provisional','simulation_supported','reality_validated','quarantined','retired')),
    sim_support_count  INTEGER NOT NULL DEFAULT 0,
    reality_prediction_ids UUID[] NOT NULL DEFAULT '{}',  -- prediction_ids that backed promotion
    promoted_at        TIMESTAMPTZ,                        -- when reality_validated was reached
    promoted_by_service TEXT,
    trusted_until      TIMESTAMPTZ,                        -- DecayTracker sets this on promotion
    producing_agent_id TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    quarantine_reason  TEXT
);

-- Trigger: block any direct SQL UPDATE that sets reality_validated
-- (the legitimate path goes through the promote_to_reality_validated() Python gate)
CREATE OR REPLACE FUNCTION enforce_reality_firewall()
RETURNS TRIGGER AS $$
BEGIN
    -- Block any attempt to set reality_validated via raw UPDATE
    -- unless it's coming from the designated resolution_service DB role
    IF NEW.validation_status = 'reality_validated'
       AND OLD.validation_status != 'reality_validated'
       AND current_user != 'resolution_service'
    THEN
        RAISE EXCEPTION
            'FIREWALL VIOLATION: only resolution_service may promote to reality_validated. '
            'Current user: %. Simulation volume does not cross the firewall.', current_user;
    END IF;
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER beliefs_reality_firewall
    BEFORE UPDATE ON beliefs
    FOR EACH ROW
    EXECUTE FUNCTION enforce_reality_firewall();

-- Prevent deletion of beliefs (audit trail)
REVOKE DELETE ON beliefs FROM PUBLIC;

CREATE INDEX IF NOT EXISTS idx_beliefs_domain_status
    ON beliefs (domain, validation_status);

CREATE INDEX IF NOT EXISTS idx_beliefs_agent
    ON beliefs (producing_agent_id);

COMMENT ON TABLE beliefs IS
    'Reality/Simulation Firewall. Only resolution_service role (via pre-registered, externally-scored '
    'predictions) may set reality_validated. sim_support_count is intentionally excluded from the '
    'promotion gate — simulation volume never crosses to reality_validated.';

COMMENT ON COLUMN beliefs.sim_support_count IS
    'Number of simulation runs supporting this belief. INTENTIONALLY IGNORED in promotion gate. '
    'Recorded for transparency only.';
