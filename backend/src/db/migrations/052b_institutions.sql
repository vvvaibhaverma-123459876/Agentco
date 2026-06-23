-- Migration 052b: Institutions Table (Civilization Layer Foundation)
-- Creates the base institutions table required by all civilization-layer features

CREATE TABLE IF NOT EXISTS institutions (
  id VARCHAR(36) PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  entity_type VARCHAR(50) NOT NULL, -- 'institution', 'department', 'team'
  parent_id VARCHAR(36),
  status VARCHAR(50) DEFAULT 'active',
  purpose TEXT,
  authority_scope JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_parent FOREIGN KEY (parent_id) REFERENCES institutions(id)
);

-- Create indices for performance
CREATE INDEX IF NOT EXISTS idx_institutions_name ON institutions(name);
CREATE INDEX IF NOT EXISTS idx_institutions_parent_id ON institutions(parent_id);
CREATE INDEX IF NOT EXISTS idx_institutions_status ON institutions(status);
CREATE INDEX IF NOT EXISTS idx_institutions_entity_type ON institutions(entity_type);

-- Specialists table: Tracks all specialists and their reputation
CREATE TABLE IF NOT EXISTS specialists (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  role VARCHAR(50) NOT NULL, -- 'researcher', 'fetcher', 'summarizer', 'validator', 'reviewer'
  name VARCHAR(255) NOT NULL,
  current_reputation NUMERIC(5, 2) DEFAULT 50.0, -- 0-100 scale
  skill_level INT DEFAULT 1, -- 1-5
  status VARCHAR(50) DEFAULT 'active',
  budget_tokens INT DEFAULT 10000,
  budget_iterations INT DEFAULT 100,
  budget_seconds INT DEFAULT 3600,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

-- Create indices for specialists
CREATE INDEX IF NOT EXISTS idx_specialists_institution_id ON specialists(institution_id);
CREATE INDEX IF NOT EXISTS idx_specialists_role ON specialists(role);
CREATE INDEX IF NOT EXISTS idx_specialists_current_reputation ON specialists(current_reputation);
CREATE INDEX IF NOT EXISTS idx_specialists_status ON specialists(status);

-- Reputation scores table
CREATE TABLE IF NOT EXISTS reputation_scores (
  id VARCHAR(36) PRIMARY KEY,
  entity_id VARCHAR(36) NOT NULL, -- specialist or institution id
  entity_type VARCHAR(50) NOT NULL, -- 'specialist', 'department', 'institution'
  role VARCHAR(50),
  score NUMERIC(5, 2) NOT NULL,
  percentile NUMERIC(5, 2),
  last_updated TIMESTAMP DEFAULT NOW(),
  CONSTRAINT check_score CHECK (score >= 0 AND score <= 100)
);

CREATE INDEX IF NOT EXISTS idx_reputation_entity_id ON reputation_scores(entity_id);
CREATE INDEX IF NOT EXISTS idx_reputation_entity_type ON reputation_scores(entity_type);
CREATE INDEX IF NOT EXISTS idx_reputation_score ON reputation_scores(score);

-- Audit log for reputation changes
CREATE TABLE IF NOT EXISTS reputation_audit_log (
  id VARCHAR(36) PRIMARY KEY,
  entity_id VARCHAR(36) NOT NULL,
  previous_reputation NUMERIC(5, 2),
  new_reputation NUMERIC(5, 2) NOT NULL,
  change_reason TEXT,
  recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_reputation_audit_entity_id ON reputation_audit_log(entity_id);
CREATE INDEX IF NOT EXISTS idx_reputation_audit_recorded_at ON reputation_audit_log(recorded_at);

-- Consistency checks table
CREATE TABLE IF NOT EXISTS consistency_checks (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36),
  check_type VARCHAR(100),
  inconsistency_found BOOLEAN DEFAULT FALSE,
  description TEXT,
  checked_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_consistency_checks_institution_id ON consistency_checks(institution_id);
CREATE INDEX IF NOT EXISTS idx_consistency_checks_checked_at ON consistency_checks(checked_at);

-- Departments table
CREATE TABLE IF NOT EXISTS departments (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  budget_allocation NUMERIC,
  status VARCHAR(50) DEFAULT 'active',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_departments_institution_id ON departments(institution_id);
CREATE INDEX IF NOT EXISTS idx_departments_name ON departments(name);
CREATE INDEX IF NOT EXISTS idx_departments_status ON departments(status);
