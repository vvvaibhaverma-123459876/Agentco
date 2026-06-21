-- Phase K: Civilization Layer MVP
-- Tables for civilization entity with constitution, laws, and governance

CREATE TABLE IF NOT EXISTS civilizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    constitution_version TEXT,
    status TEXT NOT NULL CHECK (status IN ('active','emergency','suspended','retired')),
    legitimacy_score DOUBLE PRECISION,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_civilizations_status ON civilizations(status);

CREATE TABLE IF NOT EXISTS civilization_society_edges (
    civilization_id TEXT NOT NULL REFERENCES civilizations(id),
    society_id TEXT NOT NULL REFERENCES societies(id),
    membership_status TEXT NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (civilization_id, society_id)
);

CREATE INDEX IF NOT EXISTS idx_civilization_society_edges_civ ON civilization_society_edges(civilization_id);
CREATE INDEX IF NOT EXISTS idx_civilization_society_edges_soc ON civilization_society_edges(society_id);

CREATE TABLE IF NOT EXISTS constitution_versions (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id),
    version TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    rules_json JSONB NOT NULL,
    adopted_by_decision_id TEXT,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_constitution_versions_civ ON constitution_versions(civilization_id);
CREATE INDEX IF NOT EXISTS idx_constitution_versions_active ON constitution_versions(civilization_id, active);

CREATE TABLE IF NOT EXISTS laws (
    id TEXT PRIMARY KEY,
    civilization_id TEXT REFERENCES civilizations(id),
    society_id TEXT REFERENCES societies(id),
    law_type TEXT NOT NULL,
    rule_json JSONB NOT NULL,
    status TEXT NOT NULL,
    created_by_decision_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_laws_civ ON laws(civilization_id);
CREATE INDEX IF NOT EXISTS idx_laws_society ON laws(society_id);
CREATE INDEX IF NOT EXISTS idx_laws_status ON laws(status);

CREATE TABLE IF NOT EXISTS civilization_emergency_log (
    id TEXT PRIMARY KEY,
    civilization_id TEXT NOT NULL REFERENCES civilizations(id),
    action TEXT NOT NULL,
    activated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_civilization_emergency_log_civ ON civilization_emergency_log(civilization_id);
CREATE INDEX IF NOT EXISTS idx_civilization_emergency_log_active ON civilization_emergency_log(expires_at);
