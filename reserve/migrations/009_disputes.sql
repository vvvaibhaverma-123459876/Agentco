-- Migration 009 - Dispute judiciary.

CREATE TABLE IF NOT EXISTS disputes (
    id TEXT PRIMARY KEY,
    dispute_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'opened' CHECK (status IN (
        'opened','evidence_collection','mediation','ruling_pending','ruled','appealed','final','closed'
    )),
    plaintiff_id TEXT NOT NULL,
    defendant_id TEXT NOT NULL,
    critical BOOLEAN NOT NULL DEFAULT FALSE,
    source_review_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispute_evidence (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL REFERENCES disputes(id) ON DELETE RESTRICT,
    submitted_by TEXT NOT NULL,
    evidence JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rulings (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL REFERENCES disputes(id) ON DELETE RESTRICT,
    judge_entity_id TEXT NOT NULL,
    ruling TEXT NOT NULL,
    penalty JSONB NOT NULL DEFAULT '{}',
    appeal_deadline TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS appeals (
    id TEXT PRIMARY KEY,
    ruling_id TEXT NOT NULL REFERENCES rulings(id) ON DELETE RESTRICT,
    submitted_by TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS precedents (
    id TEXT PRIMARY KEY,
    ruling_id TEXT NOT NULL REFERENCES rulings(id) ON DELETE RESTRICT,
    dispute_type TEXT NOT NULL,
    summary TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS penalties (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL REFERENCES disputes(id) ON DELETE RESTRICT,
    entity_id TEXT NOT NULL,
    penalty_type TEXT NOT NULL,
    amount DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
