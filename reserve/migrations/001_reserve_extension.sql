-- Epistemic Reserve — Phase 1 schema extension.
--
-- Extends prediction_ledger with two write-once fields:
--   hardness   — base-rate uncertainty at registration time: 2*p*(1-p) ∈ [0, 0.5].
--                Trivial predictions (p≈0 or p≈1) earn near-zero calibration credit.
--                Computed from stated probability at pre_register() time; immutable.
--   consequence — whether an entity acted on this prediction before resolution.
--                 Set once by the consequence_service role; immutable after.
--
-- Creates calibration_credentials to store signed Proof-of-Calibration credentials.
-- Each row is a snapshot of a (agent × domain × horizon) credential vector at
-- the moment of issue. Rows are append-only; a new row is issued on each refresh.

-- 1. Extend prediction_ledger.
ALTER TABLE prediction_ledger
    ADD COLUMN IF NOT EXISTS hardness    NUMERIC(5, 4) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS consequence BOOLEAN       DEFAULT FALSE;

-- Back-fill hardness for any pre-existing rows (safe: hardness is deterministic).
UPDATE prediction_ledger
   SET hardness = 2.0 * probability * (1.0 - probability)
 WHERE hardness IS NULL;

-- Make hardness NOT NULL now that the back-fill is done.
ALTER TABLE prediction_ledger
    ALTER COLUMN hardness SET NOT NULL,
    ALTER COLUMN hardness SET DEFAULT 0.0;

-- 2. Immutability: hardness is write-once (computed at registration, never changed).
--    consequence may be set from FALSE → TRUE exactly once by consequence_service.
CREATE OR REPLACE FUNCTION trg_reserve_fields_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    -- hardness must never change after set.
    IF NEW.hardness IS DISTINCT FROM OLD.hardness THEN
        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: prediction_ledger.hardness is write-once (prediction_id=%)',
            OLD.prediction_id;
    END IF;
    -- consequence may only move FALSE → TRUE, never back.
    IF OLD.consequence = TRUE AND NEW.consequence = FALSE THEN
        RAISE EXCEPTION
            'IMMUTABILITY VIOLATION: prediction_ledger.consequence cannot be reverted (prediction_id=%)',
            OLD.prediction_id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_reserve_fields_immutable ON prediction_ledger;
CREATE TRIGGER trg_reserve_fields_immutable
    BEFORE UPDATE ON prediction_ledger
    FOR EACH ROW EXECUTE FUNCTION trg_reserve_fields_immutable();

-- 3. credential_domains — one row per (agent × domain × horizon) cell in the vector.
CREATE TABLE IF NOT EXISTS credential_domains (
    cell_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         TEXT        NOT NULL,
    domain           TEXT        NOT NULL,
    horizon_class    TEXT        NOT NULL CHECK (horizon_class IN ('short', 'medium', 'long')),
    mean_log_score   NUMERIC(8, 6) NOT NULL,
    mean_brier_score NUMERIC(8, 6) NOT NULL,
    sharpness        NUMERIC(8, 6) NOT NULL,   -- mean(p*(1-p)) over resolved predictions
    sample_count     INTEGER     NOT NULL,
    last_reality_contact TIMESTAMPTZ NOT NULL,  -- resolved_at of most recent resolved prediction
    decay_half_life_days INTEGER NOT NULL,       -- domain-specific; from DecayTracker
    computed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cred_domains_agent_domain
    ON credential_domains (agent_id, domain, horizon_class);

-- 4. calibration_credentials — signed credential snapshots.
--    One row = one issued credential for one agent, covering all domains at that moment.
--    Append-only; new row on each refresh; never updated.
CREATE TABLE IF NOT EXISTS calibration_credentials (
    credential_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id         TEXT        NOT NULL,
    issued_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at       TIMESTAMPTZ NOT NULL,
    domain_cells     JSONB       NOT NULL,  -- serialized list of credential_domains cells
    overall_score    NUMERIC(8, 6) NOT NULL,
    sample_count     INTEGER     NOT NULL,
    algorithm        TEXT        NOT NULL DEFAULT 'log_score+brier/hardness_weighted/v1',
    hmac_sha256      TEXT        NOT NULL,  -- HMAC-SHA256 over canonical payload
    is_valid         BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_credentials_agent
    ON calibration_credentials (agent_id, issued_at DESC);

-- Append-only: no UPDATE or DELETE.
CREATE OR REPLACE FUNCTION trg_credentials_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'IMMUTABILITY VIOLATION: calibration_credentials is append-only';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'IMMUTABILITY VIOLATION: calibration_credentials is append-only';
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_credentials_immutable ON calibration_credentials;
CREATE TRIGGER trg_credentials_immutable
    BEFORE UPDATE OR DELETE ON calibration_credentials
    FOR EACH ROW EXECUTE FUNCTION trg_credentials_immutable();
