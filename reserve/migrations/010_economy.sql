-- Migration 010 - Institutional economy.

CREATE TABLE IF NOT EXISTS resource_accounts (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    balance DOUBLE PRECISION NOT NULL DEFAULT 0,
    locked DOUBLE PRECISION NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(entity_type, entity_id, resource_type)
);

CREATE TABLE IF NOT EXISTS resource_transactions (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES resource_accounts(id) ON DELETE RESTRICT,
    transaction_type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budget_allocations (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    allocated_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS economic_policies (
    id TEXT PRIMARY KEY,
    policy_name TEXT NOT NULL UNIQUE,
    policy JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
