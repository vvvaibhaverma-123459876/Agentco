-- Migration 007 - Society layer.

CREATE TABLE IF NOT EXISTS societies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('proposed','active','retired')),
    reputation_score DOUBLE PRECISION NULL,
    legitimacy_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS society_institution_edges (
    society_id TEXT NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
    institution_id TEXT NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('proposed','active','retired')),
    admitted_by_decision_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retired_at TIMESTAMPTZ NULL,
    PRIMARY KEY (society_id, institution_id)
);

CREATE TABLE IF NOT EXISTS society_contracts (
    society_id TEXT PRIMARY KEY REFERENCES societies(id) ON DELETE RESTRICT,
    contract JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS society_governance_decisions (
    id TEXT PRIMARY KEY,
    society_id TEXT REFERENCES societies(id) ON DELETE RESTRICT,
    decision_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','approved','rejected','executed')),
    proposer_entity_id TEXT,
    approver_entity_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS society_memory_events (
    id TEXT PRIMARY KEY,
    society_id TEXT NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL,
    summary TEXT,
    evidence_refs JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS society_reputation_snapshots (
    id TEXT PRIMARY KEY,
    society_id TEXT NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
    reputation_score DOUBLE PRECISION,
    unresolved_dispute_count INTEGER NOT NULL DEFAULT 0,
    repeated_failure_count INTEGER NOT NULL DEFAULT 0,
    governance_compliance_score DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    high_risk_unresolved_challenge_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
