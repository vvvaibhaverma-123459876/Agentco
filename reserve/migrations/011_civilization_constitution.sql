-- Migration 011 - Civilization constitution and law registry.

CREATE TABLE IF NOT EXISTS civilizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'active',
    active_constitution_version_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS civilization_society_edges (
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    society_id TEXT NOT NULL REFERENCES societies(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'active',
    admitted_by_amendment_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (civilization_id, society_id)
);

CREATE TABLE IF NOT EXISTS constitution_versions (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    version TEXT NOT NULL,
    constitution JSONB NOT NULL,
    adopted BOOLEAN NOT NULL DEFAULT FALSE,
    quorum_count INTEGER NOT NULL,
    external_approval_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS laws (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    law_code TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    constitution_version_id TEXT REFERENCES constitution_versions(id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS constitutional_amendments (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','adopted','rejected')),
    proposed_by TEXT NOT NULL,
    external_approval_id TEXT,
    quorum_count INTEGER NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emergency_states (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    reason TEXT NOT NULL,
    declared_by TEXT NOT NULL,
    valid_until TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS civilization_constitution_memory_events (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
    event_type TEXT NOT NULL,
    summary TEXT,
    evidence_refs JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
