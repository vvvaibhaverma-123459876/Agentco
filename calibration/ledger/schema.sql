-- =============================================================================
-- PREDICTION LEDGER — immutable, append-only
-- The legal and epistemic record of every falsifiable claim made in AgentCo.
--
-- Immutability is enforced at THREE layers:
--   1. DB roles: predicting agents have INSERT only (not UPDATE, not DELETE)
--   2. Trigger: rejects any UPDATE touching pre-registration columns
--   3. Trigger: allows resolution columns to be set exactly ONCE, ONLY by
--      resolution_service role, ONLY at/after resolution_date
-- =============================================================================

CREATE TABLE IF NOT EXISTS prediction_ledger (
    prediction_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- PRE-REGISTRATION FIELDS (set at INSERT, immutable thereafter)
    claim                TEXT        NOT NULL,
    probability          NUMERIC     NOT NULL CHECK (probability >= 0 AND probability <= 1),
    confidence_basis     JSONB       NOT NULL,   -- principles/theories/data the prediction rests on
    producing_agent_id   TEXT        NOT NULL,
    producing_prompt_ver TEXT        NOT NULL,   -- exact semantic version of the prompt
    resolution_criterion TEXT        NOT NULL,   -- unambiguous true/false test
    resolution_date      TIMESTAMPTZ NOT NULL,   -- set at creation; NEVER editable
    ground_truth_source  TEXT        NOT NULL,   -- MUST be external to the reasoning system
    horizon_class        TEXT        NOT NULL CHECK (horizon_class IN ('short','medium','long')),
    domain               TEXT        NOT NULL,
    claim_type           TEXT        NOT NULL,
    correlation_id       UUID,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- post_hoc: set TRUE by ingestion path if created_at > earliest_knowable_at
    -- A post_hoc prediction is EXCLUDED from all calibration math
    post_hoc             BOOLEAN     NOT NULL DEFAULT false,
    earliest_knowable_at TIMESTAMPTZ,           -- if known; used by post-hoc detection

    -- RESOLUTION FIELDS — write-once, by resolution_service role only, at/after resolution_date
    resolved             BOOLEAN     NOT NULL DEFAULT false,
    resolved_outcome     BOOLEAN,               -- true/false; null until resolved
    resolved_at          TIMESTAMPTZ,
    resolved_by_service  TEXT,                  -- identity of the resolution service instance
    brier_score          NUMERIC,               -- (outcome - probability)^2
    log_score            NUMERIC,               -- log(probability) if true, log(1-p) if false
    was_surprise         BOOLEAN     NOT NULL DEFAULT false  -- flagged by Surprise Register
);

-- =============================================================================
-- IMMUTABILITY ENFORCEMENT
-- =============================================================================

-- Trigger: block any UPDATE to pre-registration columns after INSERT
CREATE OR REPLACE FUNCTION enforce_prediction_immutability()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    immutable_cols TEXT[] := ARRAY[
        'claim','probability','confidence_basis','producing_agent_id',
        'producing_prompt_ver','resolution_criterion','resolution_date',
        'ground_truth_source','horizon_class','domain','claim_type',
        'correlation_id','created_at','post_hoc','earliest_knowable_at'
    ];
    col TEXT;
BEGIN
    FOREACH col IN ARRAY immutable_cols LOOP
        IF to_jsonb(NEW) -> col IS DISTINCT FROM to_jsonb(OLD) -> col THEN
            RAISE EXCEPTION 'IMMUTABILITY VIOLATION: column % on prediction_ledger is read-only after insert. prediction_id=%', col, OLD.prediction_id;
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER prediction_immutability_guard
    BEFORE UPDATE ON prediction_ledger
    FOR EACH ROW EXECUTE FUNCTION enforce_prediction_immutability();

-- Trigger: resolution columns may be set ONCE, ONLY at/after resolution_date,
--          ONLY by current_user = 'resolution_service'
CREATE OR REPLACE FUNCTION enforce_resolution_write_once()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- Enforce role restriction
    IF current_user != 'resolution_service' THEN
        RAISE EXCEPTION 'PERMISSION DENIED: only resolution_service may write resolution columns. current_user=%', current_user;
    END IF;
    -- Enforce time gate
    IF now() < OLD.resolution_date THEN
        RAISE EXCEPTION 'TIME GATE: cannot resolve prediction before resolution_date (now=%, resolution_date=%)',
            now(), OLD.resolution_date;
    END IF;
    -- Enforce write-once: reject if already resolved
    IF OLD.resolved = true THEN
        RAISE EXCEPTION 'WRITE-ONCE VIOLATION: prediction % is already resolved', OLD.prediction_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER resolution_write_once_guard
    BEFORE UPDATE OF resolved, resolved_outcome, resolved_at, resolved_by_service,
                      brier_score, log_score, was_surprise
    ON prediction_ledger
    FOR EACH ROW EXECUTE FUNCTION enforce_resolution_write_once();

-- Indexes for common query patterns
CREATE INDEX idx_pl_agent       ON prediction_ledger(producing_agent_id);
CREATE INDEX idx_pl_domain      ON prediction_ledger(domain, claim_type);
CREATE INDEX idx_pl_horizon     ON prediction_ledger(horizon_class);
CREATE INDEX idx_pl_resolution  ON prediction_ledger(resolution_date) WHERE NOT resolved;
CREATE INDEX idx_pl_post_hoc    ON prediction_ledger(post_hoc) WHERE post_hoc = true;
CREATE INDEX idx_pl_correlation ON prediction_ledger(correlation_id);
CREATE INDEX idx_pl_unresolved  ON prediction_ledger(resolved) WHERE resolved = false;

-- =============================================================================
-- DB ROLE GRANTS (run as superuser during setup)
-- =============================================================================
-- REVOKE ALL ON prediction_ledger FROM PUBLIC;
-- GRANT INSERT              ON prediction_ledger TO agent_role;   -- agents: insert only
-- GRANT SELECT              ON prediction_ledger TO agent_role;
-- GRANT SELECT, UPDATE      ON prediction_ledger TO resolution_service;
-- GRANT SELECT              ON prediction_ledger TO calibration_reader;
