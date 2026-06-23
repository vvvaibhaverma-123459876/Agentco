-- Migration: Autonomy Action Loop Support
-- Purpose: Add tables for typed action execution, evidence handling, and claim generation
-- Includes: actions, evidence, claims, searches, loop detection

-- Actions table: Tracks every decided and executed action
CREATE TABLE IF NOT EXISTS autonomy_actions (
  id VARCHAR(36) PRIMARY KEY,
  action_id VARCHAR(36) NOT NULL UNIQUE,
  action_type VARCHAR(50) NOT NULL,
  goal_id VARCHAR(36),
  plan_step_id VARCHAR(36),
  objective TEXT NOT NULL,
  args JSONB DEFAULT '{}',
  expected_artifacts TEXT[],
  success_criteria TEXT[],
  risk_level VARCHAR(20),
  decided_by VARCHAR(50),
  decided_at TIMESTAMP NOT NULL DEFAULT NOW(),
  reasoning TEXT,
  status VARCHAR(50),
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  observations JSONB DEFAULT '{}',
  created_artifacts TEXT[],
  errors TEXT[],
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_goal FOREIGN KEY (goal_id) REFERENCES autonomy_goals(id)
);

-- Evidence table: Tracks all evidence sources for claims
CREATE TABLE IF NOT EXISTS autonomy_evidence (
  id VARCHAR(36) PRIMARY KEY,
  source_id VARCHAR(36) NOT NULL UNIQUE,
  action_id VARCHAR(36),
  url TEXT NOT NULL,
  title TEXT,
  snippet TEXT,
  retrieved_at TIMESTAMP NOT NULL,
  content_hash VARCHAR(100),
  source_type VARCHAR(50), -- 'web', 'document', 'analysis', 'agent_output'
  is_public_access BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_actions(id)
);

-- Claims table: Tracks all generated claims with evidence backing
CREATE TABLE IF NOT EXISTS autonomy_claims (
  id VARCHAR(36) PRIMARY KEY,
  claim_id VARCHAR(36) NOT NULL UNIQUE,
  action_id VARCHAR(36),
  text TEXT NOT NULL,
  status VARCHAR(50), -- 'draft', 'unsupported', 'weakly_supported', 'supported', 'contradicted'
  confidence FLOAT DEFAULT 0.7,
  support_source_ids JSONB DEFAULT '[]' NOT NULL, -- JSON array of source IDs, must not be empty
  support_snippets JSONB DEFAULT '[]',
  derived_from_action_ids JSONB DEFAULT '[]',
  generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  generated_by VARCHAR(50),
  contradicts JSONB DEFAULT '[]',
  contradicted_by JSONB DEFAULT '[]',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_actions(id),
  CONSTRAINT claim_must_have_evidence CHECK (jsonb_array_length(support_source_ids) > 0)
);

-- Searches table: Tracks search decisions (precursor to web_search action execution)
CREATE TABLE IF NOT EXISTS autonomy_searches (
  id VARCHAR(36) PRIMARY KEY,
  action_id VARCHAR(36),
  query TEXT NOT NULL,
  status VARCHAR(50), -- 'initiated', 'completed', 'failed'
  results_count INT DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_actions(id)
);

-- Memory table: Tracks memory updates and learning
CREATE TABLE IF NOT EXISTS autonomy_memory (
  id VARCHAR(36) PRIMARY KEY,
  action_id VARCHAR(36),
  content JSONB NOT NULL,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_actions(id)
);

-- Loop detection table: Tracks potential loops for analysis
CREATE TABLE IF NOT EXISTS autonomy_loop_detection (
  id VARCHAR(36) PRIMARY KEY,
  goal_id VARCHAR(36),
  is_looping BOOLEAN,
  loop_type VARCHAR(50),
  streak INT,
  recommendation VARCHAR(50), -- 'replan', 'terminate', 'proceed'
  detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_goal FOREIGN KEY (goal_id) REFERENCES autonomy_goals(id)
);

-- Indexes for query performance
CREATE INDEX IF NOT EXISTS idx_actions_goal_id ON autonomy_actions(goal_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON autonomy_actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_decided_at ON autonomy_actions(decided_at);
CREATE INDEX IF NOT EXISTS idx_evidence_action_id ON autonomy_evidence(action_id);
CREATE INDEX IF NOT EXISTS idx_evidence_source_id ON autonomy_evidence(source_id);
CREATE INDEX IF NOT EXISTS idx_claims_action_id ON autonomy_claims(action_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON autonomy_claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_generated_at ON autonomy_claims(generated_at);
CREATE INDEX IF NOT EXISTS idx_searches_action_id ON autonomy_searches(action_id);
CREATE INDEX IF NOT EXISTS idx_loop_detection_goal_id ON autonomy_loop_detection(goal_id);
CREATE INDEX IF NOT EXISTS idx_claims_support_sources ON autonomy_claims USING GIN (support_source_ids);
CREATE INDEX IF NOT EXISTS idx_actions_derived_from ON autonomy_claims USING GIN (derived_from_action_ids);
