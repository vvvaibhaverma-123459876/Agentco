-- Migration 081: L2 resource ledger.
--
-- Resource accounts represent scarce civilization resources owned by actors.
-- Resource transactions are append-only records of credits/debits with a
-- canonical L3 event pointer.

CREATE TABLE IF NOT EXISTS civilization_resource_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  resource_type TEXT NOT NULL CHECK (
    resource_type IN ('compute', 'llm_tokens', 'tool_calls', 'money', 'time_seconds', 'memory_bytes', 'human_review')
  ),
  unit TEXT NOT NULL,
  balance NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (balance >= 0),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed')),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (owner_actor_id, resource_type)
);

ALTER TABLE civilization_resource_accounts
  ADD COLUMN IF NOT EXISTS reserved_balance NUMERIC(18,6) NOT NULL DEFAULT 0 CHECK (reserved_balance >= 0);

CREATE INDEX IF NOT EXISTS idx_civ_resource_accounts_owner ON civilization_resource_accounts(owner_actor_id);
CREATE INDEX IF NOT EXISTS idx_civ_resource_accounts_type ON civilization_resource_accounts(resource_type);
CREATE INDEX IF NOT EXISTS idx_civ_resource_accounts_status ON civilization_resource_accounts(status);

CREATE TABLE IF NOT EXISTS civilization_resource_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID NOT NULL REFERENCES civilization_resource_accounts(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  transaction_type TEXT NOT NULL CHECK (transaction_type IN ('credit', 'debit', 'adjustment')),
  amount NUMERIC(18,6) NOT NULL CHECK (amount > 0),
  balance_after NUMERIC(18,6) NOT NULL CHECK (balance_after >= 0),
  reason TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_civ_resource_transactions_account ON civilization_resource_transactions(account_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_civ_resource_transactions_actor ON civilization_resource_transactions(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_civ_resource_transactions_event ON civilization_resource_transactions(event_log_id);

REVOKE DELETE ON civilization_resource_transactions FROM PUBLIC;
REVOKE UPDATE ON civilization_resource_transactions FROM PUBLIC;

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

CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_account ON civilization_resource_reservations(account_id, status);
CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_actor ON civilization_resource_reservations(actor_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_civ_resource_reservations_expires ON civilization_resource_reservations(status, expires_at);

REVOKE DELETE ON civilization_resource_reservations FROM PUBLIC;
