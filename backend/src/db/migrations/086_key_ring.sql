-- Migration 086: L1 public key ring.
--
-- Stores actor public keys and lifecycle state. Private keys are never stored
-- or returned by AgentCo backend routes.

CREATE TABLE IF NOT EXISTS actor_key_ring (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  key_purpose TEXT NOT NULL CHECK (key_purpose IN ('identity', 'event_signing', 'credential_signing', 'delegation')),
  algorithm TEXT NOT NULL CHECK (algorithm IN ('ed25519')),
  public_key_pem TEXT NOT NULL,
  fingerprint_sha256 TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'rotated', 'revoked')),
  created_by UUID REFERENCES actors(id) ON DELETE RESTRICT,
  replaced_by_key_id UUID REFERENCES actor_key_ring(id) ON DELETE RESTRICT,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at TIMESTAMPTZ,
  CHECK (revoked_at IS NULL OR status IN ('rotated', 'revoked'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_actor_key_ring_one_active
  ON actor_key_ring(actor_id, key_purpose)
  WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_actor_key_ring_actor
  ON actor_key_ring(actor_id, status);
CREATE INDEX IF NOT EXISTS idx_actor_key_ring_fingerprint
  ON actor_key_ring(fingerprint_sha256);

REVOKE DELETE ON actor_key_ring FROM PUBLIC;
