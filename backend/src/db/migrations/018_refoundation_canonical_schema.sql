-- Agentco Refoundation Canonical Schema (Phase 1 baseline)
--
-- These tables are additive and idempotent. They establish the canonical
-- data contracts for claims, evidence, policy, action attestation, memory
-- events, and evaluation runs without removing legacy tables.

CREATE TABLE IF NOT EXISTS principals (
    principal_id TEXT PRIMARY KEY,
    principal_type TEXT NOT NULL CHECK (principal_type IN ('human', 'agent', 'tool', 'model_version', 'service')),
    org_id TEXT,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS constitutions (
    constitution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT,
    dsl_version TEXT NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    effective_to TIMESTAMPTZ,
    hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    constitution_id UUID REFERENCES constitutions(constitution_id),
    scope TEXT NOT NULL,
    rule_ast JSONB NOT NULL,
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high', 'critical')),
    hash TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS workflow_intents (
    intent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    requestor_id TEXT REFERENCES principals(principal_id),
    workflow_type TEXT NOT NULL,
    goal TEXT NOT NULL,
    allowed_tools TEXT[] NOT NULL DEFAULT '{}',
    risk_tier TEXT NOT NULL CHECK (risk_tier IN ('low', 'medium', 'high', 'critical'))
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    intent_id UUID REFERENCES workflow_intents(intent_id),
    claim_text TEXT NOT NULL,
    normalized_claim TEXT NOT NULL,
    domain TEXT,
    scope TEXT,
    time_horizon TEXT,
    source_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    originating_agent TEXT,
    originating_institution TEXT,
    probability DOUBLE PRECISION CHECK (probability IS NULL OR probability BETWEEN 0 AND 1),
    evidence_status TEXT NOT NULL DEFAULT 'untrusted',
    independence_class TEXT NOT NULL DEFAULT 'unresolved',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    verification_requirements JSONB NOT NULL DEFAULT '{}',
    parent_claims TEXT[] NOT NULL DEFAULT '{}',
    derived_claims TEXT[] NOT NULL DEFAULT '{}',
    contradiction_set TEXT[] NOT NULL DEFAULT '{}',
    promotion_status TEXT NOT NULL DEFAULT 'unpromoted'
);

-- Older local databases may already have a claims table from pre-refoundation
-- experiments. Add the canonical columns in place so this migration remains
-- additive instead of requiring a destructive rebuild.
ALTER TABLE claims ADD COLUMN IF NOT EXISTS intent_id UUID REFERENCES workflow_intents(intent_id);
ALTER TABLE claims ADD COLUMN IF NOT EXISTS normalized_claim TEXT NOT NULL DEFAULT '';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS scope TEXT;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS time_horizon TEXT;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS source_type TEXT NOT NULL DEFAULT 'unknown';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS source_uri TEXT NOT NULL DEFAULT '';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS originating_agent TEXT;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS originating_institution TEXT;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS evidence_status TEXT NOT NULL DEFAULT 'untrusted';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS independence_class TEXT NOT NULL DEFAULT 'unresolved';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS verification_requirements JSONB NOT NULL DEFAULT '{}';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS parent_claims TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS derived_claims TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS contradiction_set TEXT[] NOT NULL DEFAULT '{}';
ALTER TABLE claims ADD COLUMN IF NOT EXISTS promotion_status TEXT NOT NULL DEFAULT 'unpromoted';

CREATE TABLE IF NOT EXISTS evidence_artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    evidence_type TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_reliability_score DOUBLE PRECISION,
    extraction_method TEXT NOT NULL,
    supports_or_refutes TEXT NOT NULL CHECK (supports_or_refutes IN ('supports', 'refutes')),
    strength DOUBLE PRECISION NOT NULL CHECK (strength BETWEEN 0 AND 1),
    independence_group TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    mime_type TEXT,
    raw_excerpt_or_pointer TEXT,
    evaluator_agent TEXT,
    attestation_ref TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    historical_claim_count INT NOT NULL DEFAULT 0,
    resolved_true_count INT NOT NULL DEFAULT 0,
    resolved_false_count INT NOT NULL DEFAULT 0,
    unresolved_count INT NOT NULL DEFAULT 0,
    contradiction_count INT NOT NULL DEFAULT 0,
    calibration_score DOUBLE PRECISION,
    freshness TIMESTAMPTZ,
    source_type TEXT NOT NULL,
    known_bias_tags TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS resolutions (
    resolution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
    resolved_outcome TEXT NOT NULL,
    resolver_type TEXT NOT NULL,
    independence_score DOUBLE PRECISION NOT NULL CHECK (independence_score BETWEEN 0 AND 1),
    evidence_refs UUID[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (claim_id)
);

CREATE TABLE IF NOT EXISTS calibration_cells (
    cell_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id TEXT REFERENCES principals(principal_id),
    domain TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    horizon TEXT NOT NULL,
    ece DOUBLE PRECISION,
    brier DOUBLE PRECISION,
    log_score DOUBLE PRECISION,
    coverage DOUBLE PRECISION,
    n_resolved INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS action_attestations (
    action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID REFERENCES workflow_intents(intent_id),
    principal_id TEXT REFERENCES principals(principal_id),
    tool_id TEXT,
    policy_id UUID REFERENCES policies(policy_id),
    input_hash TEXT NOT NULL,
    output_hash TEXT,
    evidence_refs UUID[] NOT NULL DEFAULT '{}',
    trusted_confidence DOUBLE PRECISION CHECK (trusted_confidence IS NULL OR trusted_confidence BETWEEN 0 AND 1),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    tee_quote TEXT,
    signature_ed25519 TEXT,
    transparency_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS override_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id UUID REFERENCES action_attestations(action_id),
    opened_by TEXT REFERENCES principals(principal_id),
    status TEXT NOT NULL,
    decision TEXT,
    rationale_hash TEXT
);

CREATE TABLE IF NOT EXISTS memory_events (
    memory_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    principal_id TEXT REFERENCES principals(principal_id),
    memory_type TEXT NOT NULL,
    supersedes UUID REFERENCES memory_events(memory_id),
    content_hash TEXT NOT NULL,
    trace_id TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_eval_runs (
    eval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    benchmark TEXT NOT NULL,
    slice TEXT NOT NULL,
    model_or_agent TEXT NOT NULL,
    score DOUBLE PRECISION,
    judge_type TEXT NOT NULL,
    trace_refs TEXT[] NOT NULL DEFAULT '{}'
);
