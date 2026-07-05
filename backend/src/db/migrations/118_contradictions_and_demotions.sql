-- 118: contradiction records + memory demotions (G3 / Phase D)
-- =============================================================
-- When independent evidence proves a prediction FALSE, the beliefs built on
-- that claim must stop steering behavior — without deleting history.
--
--   contradictions   — append-only record of WHY a belief was contradicted
--                      (the false prediction, the claim, the evidence).
--   memory_demotions — append-only exclusion list; a demoted memory stays in
--                      agent_memories (append-only there too) but default
--                      retrieval skips it and the planner is warned instead.

CREATE TABLE IF NOT EXISTS contradictions (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id                 TEXT,
    prediction_id            UUID REFERENCES prediction_ledger(prediction_id),
    contradicting_source_id  TEXT,
    reason                   TEXT NOT NULL,
    detected_by              TEXT NOT NULL,
    event_log_id             UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_contradictions_claim ON contradictions(claim_id);
CREATE INDEX IF NOT EXISTS idx_contradictions_prediction ON contradictions(prediction_id);

CREATE TABLE IF NOT EXISTS memory_demotions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    memory_id        UUID NOT NULL REFERENCES agent_memories(id),
    contradiction_id UUID REFERENCES contradictions(id),
    reason           TEXT NOT NULL,
    demoted_by       TEXT NOT NULL,
    event_log_id     UUID,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- one demotion per memory: re-demoting is a no-op, not a new record
    CONSTRAINT memory_demotions_memory_unique UNIQUE (memory_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_demotions_memory ON memory_demotions(memory_id);

-- Both tables are append-only history.
CREATE OR REPLACE FUNCTION prevent_demotion_mutation() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'DEMOTION GUARD: contradiction/demotion records are append-only.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS contradictions_immutable ON contradictions;
CREATE TRIGGER contradictions_immutable
    BEFORE UPDATE OR DELETE ON contradictions
    FOR EACH ROW EXECUTE FUNCTION prevent_demotion_mutation();

DROP TRIGGER IF EXISTS memory_demotions_immutable ON memory_demotions;
CREATE TRIGGER memory_demotions_immutable
    BEFORE UPDATE OR DELETE ON memory_demotions
    FOR EACH ROW EXECUTE FUNCTION prevent_demotion_mutation();
