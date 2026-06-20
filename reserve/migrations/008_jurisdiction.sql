-- Migration 008 - Jurisdiction and delegated authority.

CREATE TABLE IF NOT EXISTS jurisdictions (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    allowed_action TEXT NOT NULL,
    allowed_output_type TEXT NOT NULL,
    constraints JSONB NOT NULL DEFAULT '{}',
    granted_by TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    reputation_requirement DOUBLE PRECISION,
    external_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS delegated_authorities (
    id TEXT PRIMARY KEY,
    parent_jurisdiction_id TEXT NOT NULL REFERENCES jurisdictions(id) ON DELETE RESTRICT,
    delegated_to_entity_type TEXT NOT NULL,
    delegated_to_entity_id TEXT NOT NULL,
    allowed_action TEXT NOT NULL,
    allowed_output_type TEXT NOT NULL,
    constraints JSONB NOT NULL DEFAULT '{}',
    valid_from TIMESTAMPTZ NOT NULL,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS authority_grants (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    jurisdiction_id TEXT NOT NULL REFERENCES jurisdictions(id) ON DELETE RESTRICT,
    granted_by TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS authority_revocations (
    id TEXT PRIMARY KEY,
    jurisdiction_id TEXT NOT NULL REFERENCES jurisdictions(id) ON DELETE RESTRICT,
    revoked_by TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
