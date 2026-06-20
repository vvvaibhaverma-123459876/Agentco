-- Migration 013 - Institution and society lifecycle evolution.

CREATE TABLE IF NOT EXISTS institution_lifecycle (
    institution_id TEXT PRIMARY KEY,
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN (
        'proposed','chartered','trial','active','probation','suspended','retired','archived'
    )),
    authority_level TEXT NOT NULL DEFAULT 'limited',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS society_lifecycle (
    society_id TEXT PRIMARY KEY,
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN (
        'proposed','chartered','active','fragmenting','merged','retired','archived'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lifecycle_events (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    summary TEXT,
    evidence_refs JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
