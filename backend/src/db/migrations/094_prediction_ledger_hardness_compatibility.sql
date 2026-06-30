-- Align the canonical prediction_ledger table with Python calibration writers,
-- which pre-register a prediction hardness score at insert time.

ALTER TABLE prediction_ledger
  ADD COLUMN IF NOT EXISTS hardness NUMERIC(6,5);

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
       OR NEW.post_hoc              IS DISTINCT FROM OLD.post_hoc
       OR NEW.hardness              IS DISTINCT FROM OLD.hardness
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
        IF current_user != 'resolution_service' THEN
            RAISE EXCEPTION
                'LEDGER RESOLUTION VIOLATION: only resolution_service may resolve predictions (current_user=%)',
                current_user;
        END IF;

        IF OLD.resolved THEN
            RAISE EXCEPTION
                'WRITE-ONCE VIOLATION: prediction % is already resolved', OLD.prediction_id;
        END IF;

        IF now() < OLD.resolution_date THEN
            RAISE EXCEPTION
                'TIME GATE VIOLATION: cannot resolve prediction % before resolution_date %',
                OLD.prediction_id, OLD.resolution_date;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
