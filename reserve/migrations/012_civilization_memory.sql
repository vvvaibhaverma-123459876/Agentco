-- Migration 012 - Civilizational memory and lineage.

CREATE TABLE IF NOT EXISTS lessons (
    id TEXT PRIMARY KEY,
    source_pattern TEXT NOT NULL,
    lesson TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    source_event_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS memory_summaries (
    id TEXT PRIMARY KEY,
    summary TEXT NOT NULL,
    raw_event_refs JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entity_genealogy (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    parent_entity_id TEXT,
    event_type TEXT NOT NULL,
    obligations JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trust_lineage (
    id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    agent_id TEXT,
    institution_id TEXT,
    society_id TEXT,
    civilization_id TEXT,
    source_refs JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS causal_links (
    id TEXT PRIMARY KEY,
    cause_event_id TEXT NOT NULL,
    effect_event_id TEXT NOT NULL,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
