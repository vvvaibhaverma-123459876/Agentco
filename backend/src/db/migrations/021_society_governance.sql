-- Society governance proposal tracking

CREATE TABLE IF NOT EXISTS society_governance_proposals (
    id TEXT PRIMARY KEY,
    society_id TEXT NOT NULL REFERENCES societies(id),
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('admission', 'amendment', 'discipline')),
    subject_id TEXT NOT NULL,
    proposed_by TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open', 'approved', 'rejected')),
    approval_votes INT DEFAULT 0,
    approval_threshold INT DEFAULT 1,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_society_governance_proposals_society ON society_governance_proposals(society_id);
CREATE INDEX IF NOT EXISTS idx_society_governance_proposals_status ON society_governance_proposals(status);

-- Dispute rulings table (append-only)
CREATE TABLE IF NOT EXISTS dispute_rulings (
    id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL,
    ruling TEXT NOT NULL,
    evidence_ref TEXT,
    issued_by_entity_id TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dispute_rulings_dispute ON dispute_rulings(dispute_id);
CREATE INDEX IF NOT EXISTS idx_dispute_rulings_issued ON dispute_rulings(issued_at);

-- Disputes table (if not already created)
CREATE TABLE IF NOT EXISTS disputes (
    id TEXT PRIMARY KEY,
    dispute_type TEXT NOT NULL,
    plaintiff_id TEXT,
    defendant_id TEXT,
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX IF NOT EXISTS idx_disputes_type ON disputes(dispute_type);
