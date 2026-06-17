-- Epistemic Reserve — Phase 3: Recursive Resolution Layer.
--
-- Credentialed oracles can resolve predictions in their domain.
-- Their authority = their cell credential weight at resolution time.
-- If contradicted by stronger downstream ground truth, they lose standing.
--
-- Contradiction chain is publicly auditable: every resolution records
-- who resolved it, with what authority, and whether it was overridden.

-- Oracle resolutions: one per (prediction_id, round).
-- Round 0 = first resolution. Round N+1 = contradiction of round N.
CREATE TABLE IF NOT EXISTS oracle_resolutions (
    resolution_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id     TEXT        NOT NULL,   -- references prediction_ledger.prediction_id
    oracle_agent_id   TEXT        NOT NULL,   -- agent acting as oracle
    credential_id     UUID,                   -- PoC credential used; NULL for external mechanical
    oracle_authority  NUMERIC(10, 6) NOT NULL CHECK (oracle_authority >= 0),
    domain            TEXT        NOT NULL,
    horizon_class     TEXT        NOT NULL,
    resolution_round  INTEGER     NOT NULL DEFAULT 0,
    outcome           BOOLEAN     NOT NULL,
    resolved_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Contradiction fields (NULL until overridden)
    contradicted      BOOLEAN     NOT NULL DEFAULT FALSE,
    contradicted_by   UUID,                   -- resolution_id of the stronger resolution
    contradicted_at   TIMESTAMPTZ,
    -- Ground truth classification
    source_type       TEXT        NOT NULL CHECK (source_type IN ('oracle', 'mechanical', 'external'))
);

CREATE INDEX IF NOT EXISTS idx_oracle_res_prediction
    ON oracle_resolutions (prediction_id, resolution_round DESC);

-- Oracle standing: running tally of (agent × domain × horizon) cells.
-- Updated on each resolution and each contradiction.
-- Append-only history; a new row is inserted on each update.
CREATE TABLE IF NOT EXISTS oracle_standing_history (
    history_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          TEXT        NOT NULL,
    domain            TEXT        NOT NULL,
    horizon_class     TEXT        NOT NULL,
    resolution_count  INTEGER     NOT NULL DEFAULT 0,
    contradiction_count INTEGER   NOT NULL DEFAULT 0,
    current_standing  NUMERIC(10, 6) NOT NULL,  -- credential weight at last update
    standing_delta    NUMERIC(10, 6) NOT NULL,   -- change from previous row
    event_type        TEXT        NOT NULL CHECK (event_type IN ('resolution', 'contradiction')),
    event_id          UUID        NOT NULL,      -- oracle_resolutions.resolution_id
    recorded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_oracle_standing_agent
    ON oracle_standing_history (agent_id, domain, horizon_class, recorded_at DESC);

-- Append-only: history rows are write-once.
CREATE OR REPLACE FUNCTION trg_oracle_history_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' OR TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'IMMUTABILITY VIOLATION: oracle_standing_history is append-only';
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_oracle_history_immutable ON oracle_standing_history;
CREATE TRIGGER trg_oracle_history_immutable
    BEFORE UPDATE OR DELETE ON oracle_standing_history
    FOR EACH ROW EXECUTE FUNCTION trg_oracle_history_immutable();
