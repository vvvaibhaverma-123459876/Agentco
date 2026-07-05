-- Close the remaining calibration hole at the database insert boundary.
--
-- Earlier migrations protected the ledger after INSERT. This migration also
-- makes registration itself falsifiable and durable:
--   - resolution_date must be after created_at;
--   - earliest_knowable_at is stored durably;
--   - post_hoc must match created_at > earliest_knowable_at;
--   - disqualified internal source tokens cannot be registered as ground truth.

ALTER TABLE prediction_ledger
  ADD COLUMN IF NOT EXISTS earliest_knowable_at TIMESTAMPTZ;

ALTER TABLE prediction_ledger
  DROP CONSTRAINT IF EXISTS prediction_ledger_resolution_after_registration,
  DROP CONSTRAINT IF EXISTS prediction_ledger_posthoc_consistent,
  DROP CONSTRAINT IF EXISTS prediction_ledger_ground_truth_external;

ALTER TABLE prediction_ledger
  ADD CONSTRAINT prediction_ledger_resolution_after_registration
    CHECK (resolution_date > created_at) NOT VALID,
  ADD CONSTRAINT prediction_ledger_posthoc_consistent
    CHECK (
      earliest_knowable_at IS NULL
      OR post_hoc = (created_at > earliest_knowable_at)
    ) NOT VALID,
  ADD CONSTRAINT prediction_ledger_ground_truth_external
    CHECK (
      NOT (
        lower(ground_truth_source) LIKE '%agentco_system%'
        OR
        regexp_split_to_array(lower(ground_truth_source), '[^a-z0-9]+')
        && ARRAY['self','internal','simulation','reasoning_system','agentco_system','twin','sandbox']
      )
    ) NOT VALID;

CREATE OR REPLACE FUNCTION enforce_prediction_ledger_immutability()
RETURNS TRIGGER AS $$
BEGIN
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
       OR NEW.hardness              IS DISTINCT FROM OLD.hardness
    THEN
        RAISE EXCEPTION
            'LEDGER IMMUTABILITY VIOLATION: pre-registration columns cannot be modified (prediction_id=%)',
            OLD.prediction_id;
    END IF;

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
