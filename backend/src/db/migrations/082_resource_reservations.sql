-- Migration 082: L2 resource reservations.
--
-- Adds two-phase reserve/settle/release support on top of the canonical L2
-- resource ledger introduced in 081.

ALTER TABLE civilization_resource_accounts
  ADD COLUMN IF NOT EXISTS reserved_balance NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (reserved_balance >= 0);

CREATE TABLE IF NOT EXISTS civilization_resource_reservations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES civilization_resource_accounts(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  amount NUMERIC(18,6) NOT NULL CHECK (amount > 0),
  status TEXT NOT NULL CHECK (status IN ('reserved', 'settled', 'released', 'expired')),
  reason TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  settled_transaction_id UUID REFERENCES civilization_resource_transactions(id) ON DELETE RESTRICT,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_account
  ON civilization_resource_reservations(account_id, status);
CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_actor
  ON civilization_resource_reservations(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_expires
  ON civilization_resource_reservations(status, expires_at);

REVOKE DELETE ON civilization_resource_reservations FROM PUBLIC;
