-- Migration: Bounded Civilization Learning Run Support
-- Purpose: Add tables for audit events and society/institution routing

-- Routed claims table: Tracks where claims are sent for review
CREATE TABLE IF NOT EXISTS autonomy_routed_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id VARCHAR(36) NOT NULL,
  destination_society VARCHAR(100) NOT NULL,
  destination_institution VARCHAR(100) NOT NULL,
  routing_reason TEXT,
  routing_confidence FLOAT DEFAULT 0.7,
  status VARCHAR(50) DEFAULT 'QUEUED_FOR_REVIEW', -- QUEUED_FOR_REVIEW, REVIEWED, APPROVED, REJECTED
  reviewed_at TIMESTAMP,
  reviewed_by VARCHAR(100),
  review_notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_claim FOREIGN KEY (claim_id) REFERENCES autonomy_claims(claim_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_routed_claims_society ON autonomy_routed_claims(destination_society);
CREATE INDEX IF NOT EXISTS idx_routed_claims_status ON autonomy_routed_claims(status);
CREATE INDEX IF NOT EXISTS idx_routed_claims_claim_id ON autonomy_routed_claims(claim_id);

-- Audit events table: Complete audit trail of learning runs
CREATE TABLE IF NOT EXISTS autonomy_audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  event_data JSONB DEFAULT '{}',
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_run_id ON autonomy_audit_events(run_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_type ON autonomy_audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON autonomy_audit_events(timestamp);

-- Source discovery runs table: Track discovery and fetch operations
CREATE TABLE IF NOT EXISTS autonomy_source_discovery_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id VARCHAR(100) NOT NULL,
  goal TEXT NOT NULL,
  source_pack VARCHAR(100) NOT NULL,
  sources_discovered INT DEFAULT 0,
  sources_allowed INT DEFAULT 0,
  sources_fetched INT DEFAULT 0,
  documents_fetched INT DEFAULT 0,
  claims_extracted INT DEFAULT 0,
  claims_persisted INT DEFAULT 0,
  claims_routed INT DEFAULT 0,
  status VARCHAR(50) DEFAULT 'COMPLETED', -- COMPLETED, FAILED, PARTIAL
  error_message TEXT,
  duration_ms INT,
  dry_run BOOLEAN DEFAULT FALSE,
  real_web_enabled BOOLEAN DEFAULT FALSE,
  provider VARCHAR(50), -- openai, local_llm, deterministic_test_only
  started_at TIMESTAMP NOT NULL,
  completed_at TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discovery_runs_run_id ON autonomy_source_discovery_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_status ON autonomy_source_discovery_runs(status);
CREATE INDEX IF NOT EXISTS idx_discovery_runs_source_pack ON autonomy_source_discovery_runs(source_pack);
