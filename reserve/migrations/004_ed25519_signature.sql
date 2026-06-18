-- Migration 004 — Add Ed25519 signature column to calibration_credentials.
--
-- Replaces the HMAC-SHA256 trust model (requires operator's secret to verify)
-- with an asymmetric Ed25519 signature (anyone verifies with the published
-- public key; the operator's private key is never required by the verifier).
--
-- The hmac_sha256 column is retained for backward-compatibility and set NULL
-- on new rows to make the migration of trust model explicit and auditable.
--
-- The public key is published at: reserve/keys/agentco_reserve_public.key
-- Key rotation: when the private key changes, a new public key file is added
-- (never deleted) so older credentials remain verifiable with their issuing key.

ALTER TABLE calibration_credentials
    ADD COLUMN IF NOT EXISTS ed25519_signature TEXT;

-- Index for fast lookup of signed credentials.
CREATE INDEX IF NOT EXISTS idx_calibration_credentials_ed25519
    ON calibration_credentials (credential_id)
    WHERE ed25519_signature IS NOT NULL;
