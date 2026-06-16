-- Trust Scores table — read by TrustController; written only by calibration pipeline
-- Records per-agent, per-domain, per-horizon calibration history.
-- Immutable rows: new calibration window creates a NEW row, never updates old ones.

CREATE TABLE IF NOT EXISTS trust_scores (
    trust_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id     TEXT NOT NULL,           -- agent_id or other producer
    subject_type   TEXT NOT NULL DEFAULT 'agent',
    domain         TEXT NOT NULL,
    claim_type     TEXT NOT NULL DEFAULT 'general',
    horizon_class  TEXT NOT NULL CHECK (horizon_class IN ('short','medium','long')),
    window_start   TIMESTAMPTZ NOT NULL,
    window_end     TIMESTAMPTZ NOT NULL,
    n_predictions  INTEGER NOT NULL DEFAULT 0,
    n_resolved     INTEGER NOT NULL DEFAULT 0,
    brier_mean     NUMERIC,
    log_mean       NUMERIC,
    ece            NUMERIC,                 -- expected calibration error; NULL until n_resolved >= 5
    trust_factor   NUMERIC NOT NULL DEFAULT 0.5 CHECK (trust_factor >= 0 AND trust_factor <= 1),
    force_downgrade BOOLEAN NOT NULL DEFAULT false,
    downgrade_reason TEXT,
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only allow inserts; no updates or deletes (immutability enforced)
REVOKE UPDATE ON trust_scores FROM PUBLIC;
REVOKE DELETE ON trust_scores FROM PUBLIC;

CREATE INDEX IF NOT EXISTS idx_trust_scores_subject
    ON trust_scores (subject_id, domain, claim_type, horizon_class);

CREATE INDEX IF NOT EXISTS idx_trust_scores_window
    ON trust_scores (window_end DESC);

COMMENT ON TABLE trust_scores IS
    'Immutable trust calibration windows. TrustController reads latest row per (subject, domain, horizon). '
    'Never update — always insert a new window row.';
