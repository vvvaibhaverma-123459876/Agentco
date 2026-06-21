-- Resolution evidence snapshots.
--
-- Append-only metadata that records why a resolution was accepted or rejected
-- as independent enough to update calibration. This table does not replace the
-- immutable prediction_ledger outcome fields; it preserves resolver identity,
-- source fingerprints, evidence hashes, and the independence verdict needed for
-- later dispute review.

CREATE TABLE IF NOT EXISTS resolution_evidence_snapshots (
    id TEXT PRIMARY KEY,
    prediction_id UUID NOT NULL REFERENCES prediction_ledger(prediction_id),
    resolver_id TEXT NOT NULL,
    resolver_type TEXT NOT NULL,
    claim_source_fingerprint JSONB NOT NULL,
    resolution_source_fingerprint JSONB NOT NULL,
    independence_verdict JSONB NOT NULL,
    evidence JSONB NOT NULL,
    evidence_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resolution_evidence_prediction
    ON resolution_evidence_snapshots (prediction_id, created_at DESC);

CREATE OR REPLACE FUNCTION trg_resolution_evidence_snapshots_append_only()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'IMMUTABILITY VIOLATION: resolution_evidence_snapshots is append-only';
END;
$$;

DROP TRIGGER IF EXISTS trg_resolution_evidence_snapshots_no_update
    ON resolution_evidence_snapshots;
CREATE TRIGGER trg_resolution_evidence_snapshots_no_update
    BEFORE UPDATE OR DELETE ON resolution_evidence_snapshots
    FOR EACH ROW EXECUTE FUNCTION trg_resolution_evidence_snapshots_append_only();

GRANT SELECT, INSERT ON resolution_evidence_snapshots TO resolution_service;

COMMENT ON TABLE resolution_evidence_snapshots IS
    'Append-only evidence metadata for resolution independence checks: resolver identity, source fingerprints, verdict, and deterministic evidence hash.';
