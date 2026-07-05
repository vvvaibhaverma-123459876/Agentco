-- Prediction Ledger — immutable, append-only, pre-registration enforced at the DB layer.
-- Mirrors calibration/ledger/prediction_ledger.py (PredictionRecord) and the
-- write-once / time-gate / role rules in calibration/resolution/resolution_service.py.
--
-- INVARIANTS enforced here (NOT in app code):
--   1. Pre-registration columns are immutable after INSERT (no agent can edit a claim).
--   2. Resolution columns are write-once (an outcome cannot be changed once recorded).
--   3. Only the `resolution_service` DB role may write resolution columns.
--   4. Resolution cannot be written before resolution_date (no pre-dating).
--   5. No UPDATE/DELETE for PUBLIC; the only legitimate UPDATE is resolution by the service role.

CREATE TABLE IF NOT EXISTS prediction_ledger (
    prediction_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Pre-registration columns (immutable after insert)
    claim                    TEXT NOT NULL,
    probability              DECIMAL(5,4) NOT NULL CHECK (probability BETWEEN 0 AND 1),
    confidence_basis         JSONB NOT NULL DEFAULT '{}',
    producing_agent_id       TEXT NOT NULL,
    producing_prompt_version TEXT NOT NULL,
    resolution_criterion     TEXT NOT NULL,
    resolution_date          TIMESTAMPTZ NOT NULL,
    ground_truth_source      TEXT NOT NULL,
    horizon_class            TEXT NOT NULL CHECK (horizon_class IN ('short','medium','long')),
    domain                   TEXT NOT NULL,
    claim_type               TEXT NOT NULL DEFAULT 'general',
    correlation_id           UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    earliest_knowable_at     TIMESTAMPTZ,
    post_hoc                 BOOLEAN NOT NULL DEFAULT false,
    -- Resolution columns (write-once, NULL until resolved by resolution_service)
    resolved                 BOOLEAN NOT NULL DEFAULT false,
    resolved_outcome         BOOLEAN,
    resolved_at              TIMESTAMPTZ,
    resolved_by_service      TEXT,
    brier_score              NUMERIC,
    log_score                NUMERIC,
    was_surprise             BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT prediction_ledger_resolution_after_registration
        CHECK (resolution_date > created_at),
    CONSTRAINT prediction_ledger_posthoc_consistent
        CHECK (
            earliest_knowable_at IS NULL
            OR post_hoc = (created_at > earliest_knowable_at)
        ),
    CONSTRAINT prediction_ledger_ground_truth_external
        CHECK (
            NOT (
                lower(ground_truth_source) LIKE '%agentco_system%'
                OR
                regexp_split_to_array(lower(ground_truth_source), '[^a-z0-9]+')
                && ARRAY['self','internal','simulation','reasoning_system','agentco_system','twin','sandbox']
            )
        )
);

-- No deletes, ever. Append-only ledger.
REVOKE DELETE ON prediction_ledger FROM PUBLIC;
-- No raw updates for PUBLIC; resolution must go through the resolution_service role.
REVOKE UPDATE ON prediction_ledger FROM PUBLIC;

-- Enforce immutability of pre-registration columns + write-once resolution + role + time gate.
CREATE OR REPLACE FUNCTION enforce_prediction_ledger_immutability()
RETURNS TRIGGER AS $$
BEGIN
    -- (1) Pre-registration columns can NEVER change after insert.
    IF NEW.claim                    IS DISTINCT FROM OLD.claim
       OR NEW.probability           IS DISTINCT FROM OLD.probability
       OR NEW.confidence_basis      IS DISTINCT FROM OLD.confidence_basis
       OR NEW.producing_agent_id    IS DISTINCT FROM OLD.producing_agent_id
       OR NEW.producing_prompt_version IS DISTINCT FROM OLD.producing_prompt_version
       OR NEW.resolution_criterion  IS DISTINCT FROM OLD.resolution_criterion
       OR NEW.resolution_date       IS DISTINCT FROM OLD.resolution_date
       OR NEW.ground_truth_source   IS DISTINCT FROM OLD.ground_truth_source
       OR NEW.horizon_class         IS DISTINCT FROM OLD.horizon_class
       OR NEW.domain                IS DISTINCT FROM OLD.domain
       OR NEW.claim_type            IS DISTINCT FROM OLD.claim_type
       OR NEW.created_at            IS DISTINCT FROM OLD.created_at
       OR NEW.earliest_knowable_at  IS DISTINCT FROM OLD.earliest_knowable_at
       OR NEW.post_hoc              IS DISTINCT FROM OLD.post_hoc
    THEN
        RAISE EXCEPTION
            'LEDGER IMMUTABILITY VIOLATION: pre-registration columns cannot be modified (prediction_id=%)',
            OLD.prediction_id;
    END IF;

    -- Any change to resolution columns is a "resolution write".
    IF (NEW.resolved IS DISTINCT FROM OLD.resolved
        OR NEW.resolved_outcome IS DISTINCT FROM OLD.resolved_outcome
        OR NEW.resolved_at IS DISTINCT FROM OLD.resolved_at
        OR NEW.resolved_by_service IS DISTINCT FROM OLD.resolved_by_service
        OR NEW.brier_score IS DISTINCT FROM OLD.brier_score
        OR NEW.log_score IS DISTINCT FROM OLD.log_score
        OR NEW.was_surprise IS DISTINCT FROM OLD.was_surprise)
    THEN
        -- (3) Only the resolution_service role may write resolution columns.
        IF current_user != 'resolution_service' THEN
            RAISE EXCEPTION
                'LEDGER RESOLUTION VIOLATION: only resolution_service may resolve predictions (current_user=%)',
                current_user;
        END IF;

        -- (2) Write-once: cannot re-resolve an already-resolved prediction.
        IF OLD.resolved THEN
            RAISE EXCEPTION
                'WRITE-ONCE VIOLATION: prediction % is already resolved', OLD.prediction_id;
        END IF;

        -- (4) Time gate: cannot resolve before resolution_date.
        IF now() < OLD.resolution_date THEN
            RAISE EXCEPTION
                'TIME GATE VIOLATION: cannot resolve prediction % before resolution_date %',
                OLD.prediction_id, OLD.resolution_date;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prediction_ledger_immutability ON prediction_ledger;
CREATE TRIGGER prediction_ledger_immutability
    BEFORE UPDATE ON prediction_ledger
    FOR EACH ROW
    EXECUTE FUNCTION enforce_prediction_ledger_immutability();

CREATE INDEX IF NOT EXISTS idx_prediction_ledger_agent
    ON prediction_ledger (producing_agent_id, domain, claim_type, horizon_class);
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_unresolved
    ON prediction_ledger (resolution_date) WHERE NOT resolved;
CREATE INDEX IF NOT EXISTS idx_prediction_ledger_posthoc
    ON prediction_ledger (post_hoc);

COMMENT ON TABLE prediction_ledger IS
    'Immutable, append-only prediction ledger. Pre-registration columns are frozen at insert; '
    'resolution columns are write-once and may be written only by the resolution_service role, '
    'only at/after resolution_date. post_hoc predictions are excluded from all calibration math.';
