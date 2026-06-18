-- Migration 005 — Tamper-evident commitment chain over resolved predictions.
--
-- PROPERTY ENFORCED AND TESTED:
--   If the operator alters, drops, or back-dates any resolved prediction that
--   feeds a score, the published chain head no longer matches the recomputed
--   log state — i.e., the tampering is DETECTABLE by any third party.
--
-- DESIGN (Certificate-Transparency style hash chain):
--   Each resolved prediction contributing to a Reserve score is "committed"
--   by appending a row to prediction_chain_log, where:
--
--     row_hash = SHA-256(prev_hash || prediction_id || agent_id ||
--                        probability || resolved_outcome || resolved_at ||
--                        domain || horizon_class || consequence)
--
--   The chain is append-only (trigger). Anyone can recompute the chain head
--   from the public prediction_ledger rows in sequence-number order and
--   compare it to the published head. A mismatch proves tampering.
--
-- This does NOT prevent the operator from altering the underlying DB row —
-- the prediction_ledger's own BEFORE UPDATE trigger does that. What this
-- adds is: a published commitment that makes any such alteration DETECTABLE
-- by a third party even if the ledger trigger were somehow bypassed.

CREATE TABLE IF NOT EXISTS prediction_chain_log (
    seq          BIGSERIAL PRIMARY KEY,        -- monotone sequence
    prediction_id UUID        NOT NULL,        -- the committed prediction
    agent_id      TEXT        NOT NULL,
    committed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    prev_hash     TEXT        NOT NULL,        -- SHA-256 of prior row (or '0'*64 for seq=1)
    row_hash      TEXT        NOT NULL UNIQUE  -- SHA-256(prev_hash || row fields)
);

-- Append-only: no UPDATE or DELETE permitted.
CREATE OR REPLACE FUNCTION trg_chain_log_immutable()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'CHAIN IMMUTABILITY VIOLATION: prediction_chain_log rows are write-once';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'CHAIN IMMUTABILITY VIOLATION: prediction_chain_log rows cannot be deleted';
    END IF;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_chain_log_immutable ON prediction_chain_log;
CREATE TRIGGER trg_chain_log_immutable
    BEFORE UPDATE OR DELETE ON prediction_chain_log
    FOR EACH ROW EXECUTE FUNCTION trg_chain_log_immutable();
