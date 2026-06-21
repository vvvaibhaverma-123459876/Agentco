CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    claim_text TEXT NOT NULL,
    claimant_id TEXT NOT NULL,
    claimant_entity_type TEXT NOT NULL,
    claimant_institution_id TEXT,
    domain TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    reality_boundary TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    probability DOUBLE PRECISION,
    status TEXT NOT NULL,
    resolution_date TIMESTAMPTZ,
    resolution_criterion TEXT,
    validation_policy_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS evidence_records (
    evidence_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    evidence_type TEXT NOT NULL,
    source_uri TEXT,
    source_fingerprint JSONB,
    content_hash TEXT,
    submitted_by TEXT NOT NULL,
    submitted_by_entity_type TEXT NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    evidence_payload JSONB NOT NULL,
    strength_score DOUBLE PRECISION,
    admissibility_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS validation_policies (
    policy_id TEXT PRIMARY KEY,
    boundary TEXT NOT NULL,
    domain TEXT,
    claim_type TEXT,
    risk_level TEXT,
    required_evidence JSONB NOT NULL,
    required_institutions JSONB NOT NULL,
    minimum_validation_ring INTEGER NOT NULL,
    external_validation_required BOOLEAN NOT NULL,
    promotion_target TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS validation_assignments (
    assignment_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    assigned_institution_id TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    result TEXT,
    reasoning_ref TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claim_disputes (
    dispute_id TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    opened_by TEXT NOT NULL,
    dispute_type TEXT NOT NULL,
    status TEXT NOT NULL,
    severity TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS claim_rulings (
    ruling_id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL REFERENCES claim_disputes(dispute_id),
    ruling_body_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    reasoning TEXT NOT NULL,
    penalties JSONB,
    precedent_created BOOLEAN NOT NULL DEFAULT FALSE,
    appeal_deadline TIMESTAMPTZ,
    final BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS claim_precedents (
    precedent_id TEXT PRIMARY KEY,
    source_ruling_id TEXT REFERENCES claim_rulings(ruling_id),
    summary TEXT NOT NULL,
    binding_scope TEXT NOT NULL,
    binding_level TEXT NOT NULL,
    applies_to_policy_ids JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scoped_authority_grants (
    grant_id TEXT PRIMARY KEY,
    grantee_entity_type TEXT NOT NULL,
    grantee_entity_id TEXT NOT NULL,
    granted_by_entity_type TEXT NOT NULL,
    granted_by_entity_id TEXT NOT NULL,
    authority_scope JSONB NOT NULL,
    allowed_actions JSONB NOT NULL,
    allowed_domains JSONB NOT NULL,
    allowed_claim_types JSONB NOT NULL,
    max_risk_level TEXT NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
