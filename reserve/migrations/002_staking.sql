-- Epistemic Reserve — Phase 2 schema.
--
-- Staking: an agent places their domain credential on a binary claim.
-- Weight is their cell score in (domain × horizon) at stake time.
-- Weighted Decision: outcome = weighted majority across all stakes.
-- Collusion resistance: fresh identities have weight ≈ 0.

-- Belief market questions — pre-registered, outcome unknown at stake time.
CREATE TABLE IF NOT EXISTS belief_questions (
    question_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim            TEXT        NOT NULL,
    domain           TEXT        NOT NULL,
    horizon_class    TEXT        NOT NULL CHECK (horizon_class IN ('short', 'medium', 'long')),
    resolution_criterion TEXT    NOT NULL,
    resolution_date  TIMESTAMPTZ NOT NULL,
    ground_truth_source TEXT     NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved         BOOLEAN     NOT NULL DEFAULT FALSE,
    resolved_outcome BOOLEAN,
    resolved_at      TIMESTAMPTZ,
    -- Weighted aggregation result (computed at resolution time)
    total_weight     NUMERIC(12, 6),
    weight_for_true  NUMERIC(12, 6),
    weight_for_false NUMERIC(12, 6),
    weighted_outcome BOOLEAN
);

-- Stakes — write-once at stake time; never modified.
-- weight is the agent's cell_log_score in the matching (domain × horizon) at stake time.
-- We floor-clip to 0 so negative log scores don't invert the weighting.
CREATE TABLE IF NOT EXISTS belief_stakes (
    stake_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id      UUID        NOT NULL REFERENCES belief_questions(question_id),
    agent_id         TEXT        NOT NULL,
    credential_id    UUID        NOT NULL REFERENCES calibration_credentials(credential_id),
    domain           TEXT        NOT NULL,
    horizon_class    TEXT        NOT NULL,
    -- weight = max(0, cell_log_score_at_stake_time)
    -- negative log scores map to 0 (no negative voting power)
    stake_weight     NUMERIC(10, 6) NOT NULL CHECK (stake_weight >= 0),
    position         BOOLEAN     NOT NULL,    -- TRUE = staking "yes", FALSE = staking "no"
    staked_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (question_id, agent_id)             -- one stake per agent per question
);

-- Append-only: stakes are write-once.
CREATE OR REPLACE FUNCTION trg_stakes_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'IMMUTABILITY VIOLATION: belief_stakes is write-once';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'IMMUTABILITY VIOLATION: belief_stakes is write-once';
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_stakes_immutable ON belief_stakes;
CREATE TRIGGER trg_stakes_immutable
    BEFORE UPDATE OR DELETE ON belief_stakes
    FOR EACH ROW EXECUTE FUNCTION trg_stakes_immutable();

-- Pre-stake time gate: cannot stake after question is resolved.
CREATE OR REPLACE FUNCTION trg_stake_time_gate()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE
    q_resolved BOOLEAN;
BEGIN
    SELECT resolved INTO q_resolved FROM belief_questions WHERE question_id = NEW.question_id;
    IF q_resolved THEN
        RAISE EXCEPTION 'TIME GATE: cannot stake on already-resolved question %', NEW.question_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_stake_time_gate ON belief_stakes;
CREATE TRIGGER trg_stake_time_gate
    BEFORE INSERT ON belief_stakes
    FOR EACH ROW EXECUTE FUNCTION trg_stake_time_gate();
