-- Migration 035: Simulation environment infrastructure
--
-- Deterministic simulators for safe learning. Reality/Simulation firewall
-- prevents simulation outputs from becoming ground truth.

CREATE TABLE IF NOT EXISTS simulator_configs (
    id TEXT PRIMARY KEY,
    simulator_type TEXT NOT NULL CHECK (simulator_type IN (
        'business_decision_sim',
        'research_claim_sim',
        'environment_sim',
        'custom'
    )),
    name TEXT NOT NULL,
    description TEXT,
    version TEXT NOT NULL,
    seed INT,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    deterministic BOOLEAN NOT NULL DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulator_configs_simulator_type ON simulator_configs(simulator_type);


-- Simulator runs
CREATE TABLE IF NOT EXISTS simulator_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_config_id TEXT NOT NULL REFERENCES simulator_configs(id),
    run_type TEXT NOT NULL CHECK (run_type IN (
        'training',
        'evaluation',
        'exploration',
        'validation'
    )),
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN (
        'pending',
        'running',
        'completed',
        'failed',
        'cancelled'
    )),
    agent_id TEXT,
    seed_used INT,
    total_steps INT NOT NULL DEFAULT 0,
    total_reward FLOAT NOT NULL DEFAULT 0.0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_simulator_runs_simulator_config_id ON simulator_runs(simulator_config_id);
CREATE INDEX IF NOT EXISTS idx_simulator_runs_status ON simulator_runs(status);
CREATE INDEX IF NOT EXISTS idx_simulator_runs_created_at ON simulator_runs(created_at);


-- Individual steps within simulation run
CREATE TABLE IF NOT EXISTS simulator_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_run_id UUID NOT NULL REFERENCES simulator_runs(id),
    step_index INT NOT NULL,
    state_json JSONB NOT NULL,
    action_json JSONB NOT NULL,
    observation_json JSONB NOT NULL,
    reward FLOAT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT false,
    info_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(simulator_run_id, step_index)
);

CREATE INDEX IF NOT EXISTS idx_simulator_steps_simulator_run_id ON simulator_steps(simulator_run_id);


-- Simulator outcomes
CREATE TABLE IF NOT EXISTS simulator_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_run_id UUID NOT NULL REFERENCES simulator_runs(id),
    outcome_type TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    final_score FLOAT,
    evaluation_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulator_outcomes_simulator_run_id ON simulator_outcomes(simulator_run_id);
CREATE INDEX IF NOT EXISTS idx_simulator_outcomes_success ON simulator_outcomes(success);


-- Reality/Simulation firewall marker
CREATE TABLE IF NOT EXISTS simulation_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    simulator_run_id UUID NOT NULL REFERENCES simulator_runs(id),
    output_type TEXT NOT NULL CHECK (output_type IN (
        'trajectory',
        'trajectory_batch',
        'outcome',
        'metric',
        'candidate'
    )),
    output_id TEXT NOT NULL,
    marked_as_simulation BOOLEAN NOT NULL DEFAULT true,
    can_promote_to_production BOOLEAN NOT NULL DEFAULT false,
    reason_if_producible TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulation_outputs_simulator_run_id ON simulation_outputs(simulator_run_id);
CREATE INDEX IF NOT EXISTS idx_simulation_outputs_output_type ON simulation_outputs(output_type);


-- Enforce Reality/Simulation firewall: simulation outputs cannot be promoted without explicit approval
CREATE OR REPLACE FUNCTION check_simulation_firewall(
    p_output_id TEXT
) RETURNS TABLE(is_simulation_output BOOLEAN, can_promote BOOLEAN, reason TEXT) AS $$
DECLARE
    v_is_simulation BOOLEAN;
    v_can_promote BOOLEAN;
BEGIN
    SELECT marked_as_simulation, can_promote_to_production
    INTO v_is_simulation, v_can_promote
    FROM simulation_outputs
    WHERE output_id = p_output_id;

    -- If not found, not a simulation output
    IF v_is_simulation IS NULL THEN
        RETURN QUERY SELECT false, true, 'Not a simulation output'::TEXT;
    ELSE
        RETURN QUERY SELECT v_is_simulation, v_can_promote, 'Simulation output, ' ||
            CASE WHEN v_can_promote THEN 'approved for production' ELSE 'not approved for production' END;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- Immutable: simulator runs and outcomes
CREATE TRIGGER simulator_runs_immutable_after_created
    BEFORE UPDATE ON simulator_runs
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('simulator_runs');

CREATE TRIGGER simulator_outcomes_immutable_after_created
    BEFORE UPDATE ON simulator_outcomes
    FOR EACH ROW EXECUTE FUNCTION raise_immutability_violation('simulator_outcomes');
