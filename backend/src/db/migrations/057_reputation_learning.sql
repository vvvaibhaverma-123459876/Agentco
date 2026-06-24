-- REPUTATION LEARNING SYSTEM
-- Tracks performance and learning across all entity types

-- Core reputation scores table
CREATE TABLE IF NOT EXISTS reputation_scores (
  entity_id VARCHAR(36) PRIMARY KEY,
  entity_type VARCHAR(50) NOT NULL,  -- agent, team, institution, society
  current_score NUMERIC(5, 2) NOT NULL DEFAULT 50.0,  -- 0-100

  -- Dimensional scores (0-1)
  reliability NUMERIC(3, 2) NOT NULL DEFAULT 0.5,
  speed NUMERIC(3, 2) NOT NULL DEFAULT 0.5,
  innovation NUMERIC(3, 2) NOT NULL DEFAULT 0.5,
  collaboration NUMERIC(3, 2) NOT NULL DEFAULT 0.5,

  -- Performance history (JSON array of events)
  performance_history JSONB NOT NULL DEFAULT '[]',

  -- Specialization areas (JSON array of strings)
  specialization JSONB NOT NULL DEFAULT '[]',

  -- Timestamps
  last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reputation_entity_type ON reputation_scores(entity_type);
CREATE INDEX IF NOT EXISTS idx_reputation_score ON reputation_scores(current_score);
CREATE INDEX IF NOT EXISTS idx_reputation_last_updated ON reputation_scores(last_updated);

-- Audit log for all reputation events
CREATE TABLE IF NOT EXISTS reputation_audit_log (
  event_id VARCHAR(36) PRIMARY KEY,
  entity_id VARCHAR(36) NOT NULL,
  event_type VARCHAR(50) NOT NULL,  -- claim_verified, claim_refuted, research_completed, governance_voted, coordination_success, coordination_failure
  magnitude NUMERIC(3, 2) NOT NULL,  -- -1.0 to 1.0, impact of event

  -- Related entities involved in this event (JSON array)
  related_entities JSONB NOT NULL DEFAULT '[]',

  -- Event context (arbitrary JSON data)
  context JSONB NOT NULL DEFAULT '{}',

  -- Timestamps
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_audit_entity FOREIGN KEY (entity_id) REFERENCES reputation_scores(entity_id) ON DELETE CASCADE
);

-- Create indexes for audit log
CREATE INDEX IF NOT EXISTS idx_audit_entity ON reputation_audit_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON reputation_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON reputation_audit_log(timestamp);

-- Entity hierarchy for cascade operations
CREATE TABLE IF NOT EXISTS entity_hierarchy (
  child_id VARCHAR(36) NOT NULL,
  parent_id VARCHAR(36) NOT NULL,
  relationship_type VARCHAR(50) NOT NULL,  -- agent_to_team, team_to_institution, institution_to_society
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  PRIMARY KEY (child_id, parent_id),
  CONSTRAINT fk_child FOREIGN KEY (child_id) REFERENCES reputation_scores(entity_id) ON DELETE CASCADE,
  CONSTRAINT fk_parent FOREIGN KEY (parent_id) REFERENCES reputation_scores(entity_id) ON DELETE CASCADE
);

-- Create indexes for hierarchy traversal
CREATE INDEX IF NOT EXISTS idx_hierarchy_parent ON entity_hierarchy(parent_id);
CREATE INDEX IF NOT EXISTS idx_hierarchy_child ON entity_hierarchy(child_id);
CREATE INDEX IF NOT EXISTS idx_hierarchy_type ON entity_hierarchy(relationship_type);

-- Specialization tracking
CREATE TABLE IF NOT EXISTS specialization_records (
  specialization_id VARCHAR(36) PRIMARY KEY,
  entity_id VARCHAR(36) NOT NULL,
  domain VARCHAR(100) NOT NULL,
  proficiency NUMERIC(3, 2) NOT NULL DEFAULT 0.5,  -- 0-1
  success_count INT NOT NULL DEFAULT 0,
  total_attempts INT NOT NULL DEFAULT 0,
  last_successful TIMESTAMP,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_spec_entity FOREIGN KEY (entity_id) REFERENCES reputation_scores(entity_id) ON DELETE CASCADE
);

-- Create indexes for specialization
CREATE INDEX IF NOT EXISTS idx_specialization_entity ON specialization_records(entity_id);
CREATE INDEX IF NOT EXISTS idx_specialization_domain ON specialization_records(domain);
CREATE INDEX IF NOT EXISTS idx_specialization_proficiency ON specialization_records(proficiency);
