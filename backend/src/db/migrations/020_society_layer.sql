-- Phase J: Society Layer MVP
-- Tables for multi-institution societies with governance and reputation aggregation

CREATE TABLE IF NOT EXISTS societies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active','suspended','retired')),
    authority_scope JSONB NOT NULL DEFAULT '[]',
    reputation_score DOUBLE PRECISION,
    constitution_ref TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_societies_status ON societies(status);
CREATE INDEX IF NOT EXISTS idx_societies_domain ON societies(domain);

CREATE TABLE IF NOT EXISTS society_institution_edges (
    society_id TEXT NOT NULL REFERENCES societies(id),
    institution_id TEXT NOT NULL REFERENCES institutions(id),
    membership_status TEXT NOT NULL CHECK (membership_status IN (
        'proposed','active','suspended','retired'
    )),
    role TEXT NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (society_id, institution_id)
);

CREATE INDEX IF NOT EXISTS idx_society_institution_edges_status ON society_institution_edges(membership_status);
CREATE INDEX IF NOT EXISTS idx_society_institution_edges_society ON society_institution_edges(society_id);
CREATE INDEX IF NOT EXISTS idx_society_institution_edges_institution ON society_institution_edges(institution_id);

-- Append-only audit trail for society changes
CREATE TABLE IF NOT EXISTS society_audit_log (
    id TEXT PRIMARY KEY,
    society_id TEXT NOT NULL REFERENCES societies(id),
    action TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_society_audit_log_society ON society_audit_log(society_id);
CREATE INDEX IF NOT EXISTS idx_society_audit_log_created ON society_audit_log(created_at);
