-- Migration: Calibration Framework for Phase 5 Self-Modification
-- Purpose: Track claim accuracy and build trustworthiness models
-- Governance: No self-modification without real calibration data

-- Claims validation table: Ground truth for extracted claims
CREATE TABLE IF NOT EXISTS autonomy_claim_validations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id VARCHAR(36) NOT NULL,
  validation_timestamp TIMESTAMP NOT NULL,
  validation_source VARCHAR(100), -- 'human_review', 'external_api', 'community_feedback', 'ground_truth_db'
  actual_outcome VARCHAR(50), -- 'TRUE', 'FALSE', 'PARTIAL', 'UNRESOLVED', 'UNKNOWN'
  confidence FLOAT DEFAULT 0.5, -- How confident is this validation
  evidence_for_validation TEXT, -- Link or explanation
  validator_notes TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_claim FOREIGN KEY (claim_id) REFERENCES autonomy_claims(claim_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validations_claim_id ON autonomy_claim_validations(claim_id);
CREATE INDEX IF NOT EXISTS idx_validations_outcome ON autonomy_claim_validations(actual_outcome);
CREATE INDEX IF NOT EXISTS idx_validations_timestamp ON autonomy_claim_validations(validation_timestamp);

-- Provider calibration scores: Accuracy metrics by extraction provider
CREATE TABLE IF NOT EXISTS autonomy_provider_calibration (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider VARCHAR(100) NOT NULL, -- 'openai', 'local_llm', etc.
  source_pack VARCHAR(100), -- NULL = overall, specific pack = by source pack
  measurement_period_start TIMESTAMP NOT NULL,
  measurement_period_end TIMESTAMP NOT NULL,

  -- Raw metrics
  claims_extracted INT DEFAULT 0,
  claims_validated INT DEFAULT 0,
  claims_true INT DEFAULT 0,
  claims_false INT DEFAULT 0,
  claims_partial INT DEFAULT 0,
  claims_unresolved INT DEFAULT 0,

  -- Computed metrics
  accuracy FLOAT, -- claims_true / claims_validated (if validated > 0)
  precision FLOAT, -- true_positives / (true_positives + false_positives)
  recall FLOAT, -- true_positives / (true_positives + false_negatives)
  f1_score FLOAT,

  -- Confidence
  confidence_in_measurement FLOAT DEFAULT 0.5, -- Based on sample size
  minimum_samples_needed INT DEFAULT 10,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT unique_provider_period UNIQUE(provider, source_pack, measurement_period_start, measurement_period_end)
);

CREATE INDEX IF NOT EXISTS idx_calibration_provider ON autonomy_provider_calibration(provider);
CREATE INDEX IF NOT EXISTS idx_calibration_source_pack ON autonomy_provider_calibration(source_pack);
CREATE INDEX IF NOT EXISTS idx_calibration_period ON autonomy_provider_calibration(measurement_period_start);

-- Source trustworthiness: Track which sources produce accurate claims
CREATE TABLE IF NOT EXISTS autonomy_source_trustworthiness (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_domain VARCHAR(255) NOT NULL,
  source_pack VARCHAR(100),
  measurement_period_start TIMESTAMP NOT NULL,
  measurement_period_end TIMESTAMP NOT NULL,

  -- Raw metrics
  claims_extracted INT DEFAULT 0,
  claims_validated INT DEFAULT 0,
  accuracy FLOAT, -- true claims / total validated

  -- Trust tier based on accuracy
  trust_tier VARCHAR(50), -- 'TRUSTED', 'UNCERTAIN', 'UNRELIABLE', 'BLOCKED'
  reason_for_tier TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT unique_source_period UNIQUE(source_domain, source_pack, measurement_period_start, measurement_period_end)
);

CREATE INDEX IF NOT EXISTS idx_trustworthiness_domain ON autonomy_source_trustworthiness(source_domain);
CREATE INDEX IF NOT EXISTS idx_trustworthiness_tier ON autonomy_source_trustworthiness(trust_tier);

-- Calibration events: Log all calibration operations
CREATE TABLE IF NOT EXISTS autonomy_calibration_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type VARCHAR(100) NOT NULL, -- 'validation_recorded', 'metrics_computed', 'tier_updated'
  run_id VARCHAR(100),
  claim_id VARCHAR(36),
  provider VARCHAR(100),
  event_data JSONB DEFAULT '{}',
  timestamp TIMESTAMP NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calib_events_type ON autonomy_calibration_events(event_type);
CREATE INDEX IF NOT EXISTS idx_calib_events_timestamp ON autonomy_calibration_events(timestamp);

-- Self-modification approval gates: What changes are permitted based on calibration
CREATE TABLE IF NOT EXISTS autonomy_self_mod_gates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  gate_name VARCHAR(100) NOT NULL UNIQUE, -- 'PROVIDER_ACCURACY', 'SOURCE_TRUST', 'DECISION_QUALITY'
  gate_type VARCHAR(50), -- 'METRIC_THRESHOLD', 'EXPERT_APPROVAL', 'COMMUNITY_VOTE'
  enabled BOOLEAN DEFAULT FALSE,

  -- Gate requirements
  required_metric VARCHAR(100), -- e.g. 'accuracy', 'f1_score'
  required_threshold FLOAT, -- e.g. 0.85 for 85% accuracy
  minimum_sample_size INT DEFAULT 10,

  -- Evidence requirements
  evidence_required TEXT, -- What proof is needed before self-mod allowed
  approval_required_from VARCHAR(100), -- 'human', 'expert_panel', 'community'

  -- Status
  last_evaluated TIMESTAMP,
  passes_gate BOOLEAN DEFAULT FALSE,
  failure_reason TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gates_enabled ON autonomy_self_mod_gates(enabled);
CREATE INDEX IF NOT EXISTS idx_gates_passes ON autonomy_self_mod_gates(passes_gate);

-- Calibration report: High-level summary of system trustworthiness
CREATE TABLE IF NOT EXISTS autonomy_calibration_reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_period_start TIMESTAMP NOT NULL,
  report_period_end TIMESTAMP NOT NULL,

  -- Overall metrics
  total_claims_extracted INT DEFAULT 0,
  total_claims_validated INT DEFAULT 0,
  overall_accuracy FLOAT,
  validation_coverage FLOAT, -- % of claims that have been validated

  -- Provider performance
  best_provider VARCHAR(100),
  best_provider_accuracy FLOAT,
  worst_provider VARCHAR(100),
  worst_provider_accuracy FLOAT,

  -- Source performance
  best_source_domain VARCHAR(255),
  best_source_accuracy FLOAT,
  blocked_sources INT DEFAULT 0,

  -- Phase 5 readiness
  phase5_ready BOOLEAN DEFAULT FALSE,
  phase5_blockers TEXT[], -- Array of what's preventing self-mod

  -- Recommendations
  recommendations TEXT,

  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reports_period ON autonomy_calibration_reports(report_period_start);
CREATE INDEX IF NOT EXISTS idx_reports_ready ON autonomy_calibration_reports(phase5_ready);

-- Initialize default gates (all disabled until calibration data exists)
INSERT INTO autonomy_self_mod_gates (
  gate_name, gate_type, enabled, required_metric, required_threshold,
  minimum_sample_size, evidence_required, approval_required_from
) VALUES
  ('PROVIDER_ACCURACY', 'METRIC_THRESHOLD', FALSE, 'accuracy', 0.85, 10,
   'Minimum 10 validated claims per provider with >85% accuracy', 'expert_panel'),
  ('SOURCE_TRUST', 'METRIC_THRESHOLD', FALSE, 'accuracy', 0.80, 5,
   'Source domains with >80% claim accuracy on minimum 5 claims', 'expert_panel'),
  ('DECISION_QUALITY', 'METRIC_THRESHOLD', FALSE, 'f1_score', 0.80, 10,
   'LLM decision quality >80% F1 score on real validation data', 'expert_panel')
ON CONFLICT (gate_name) DO NOTHING;
