-- Migration 053: Work Assignment Schema
-- Adds tables for institution-autonomy integration
-- Date: 2026-06-23

-- Track work requests from institutions to autonomy system
CREATE TABLE IF NOT EXISTS institution_work_requests (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  department_id VARCHAR(36) NOT NULL,
  objective TEXT NOT NULL,
  required_specialists JSONB NOT NULL DEFAULT '[]',
  budget_tokens INT NOT NULL,
  budget_iterations INT NOT NULL,
  budget_seconds INT NOT NULL,
  verification_required BOOLEAN DEFAULT FALSE,
  external_reviewer_id VARCHAR(36),
  reputation_metric VARCHAR(100),
  risk_level VARCHAR(50) DEFAULT 'low',
  status VARCHAR(50) DEFAULT 'queued',
  autonomy_goal_id VARCHAR(36),
  result_summary JSONB,
  specialist_performance JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id),
  CONSTRAINT fk_department FOREIGN KEY (department_id) REFERENCES departments(id),
  CONSTRAINT status_check CHECK (status IN ('queued', 'in_progress', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_work_requests_institution ON institution_work_requests(institution_id);
CREATE INDEX IF NOT EXISTS idx_work_requests_department ON institution_work_requests(department_id);
CREATE INDEX IF NOT EXISTS idx_work_requests_status ON institution_work_requests(status);
CREATE INDEX IF NOT EXISTS idx_work_requests_goal ON institution_work_requests(autonomy_goal_id);

-- Track specialist assignments to departments
CREATE TABLE IF NOT EXISTS institution_specialist_assignments (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  department_id VARCHAR(36) NOT NULL,
  specialist_role VARCHAR(100) NOT NULL,
  reputation_score NUMERIC(5, 2) DEFAULT 0.0,
  active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id),
  CONSTRAINT fk_department FOREIGN KEY (department_id) REFERENCES departments(id),
  UNIQUE(department_id, specialist_role)
);

CREATE INDEX IF NOT EXISTS idx_assignments_institution ON institution_specialist_assignments(institution_id);
CREATE INDEX IF NOT EXISTS idx_assignments_department ON institution_specialist_assignments(department_id);
CREATE INDEX IF NOT EXISTS idx_assignments_role ON institution_specialist_assignments(specialist_role);

-- Track specialist performance for work requests
CREATE TABLE IF NOT EXISTS specialist_performance_history (
  id VARCHAR(36) PRIMARY KEY,
  work_request_id VARCHAR(36) NOT NULL,
  specialist_role VARCHAR(100) NOT NULL,
  evidence_quality_score NUMERIC(3, 2),
  claim_accuracy_score NUMERIC(3, 2),
  efficiency_score NUMERIC(3, 2),
  overall_score NUMERIC(3, 2),
  tokens_used INT,
  iterations_used INT,
  time_elapsed_seconds INT,
  completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_work_request FOREIGN KEY (work_request_id) REFERENCES institution_work_requests(id)
);

CREATE INDEX IF NOT EXISTS idx_perf_work_request ON specialist_performance_history(work_request_id);
CREATE INDEX IF NOT EXISTS idx_perf_specialist ON specialist_performance_history(specialist_role);
CREATE INDEX IF NOT EXISTS idx_perf_overall_score ON specialist_performance_history(overall_score);

-- Track work cycle completion for audit trail
CREATE TABLE IF NOT EXISTS work_cycle_events (
  id VARCHAR(36) PRIMARY KEY,
  work_request_id VARCHAR(36) NOT NULL,
  cycle_phase VARCHAR(100) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  details JSONB,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_work_request FOREIGN KEY (work_request_id) REFERENCES institution_work_requests(id)
);

CREATE INDEX IF NOT EXISTS idx_cycle_work_request ON work_cycle_events(work_request_id);
CREATE INDEX IF NOT EXISTS idx_cycle_timestamp ON work_cycle_events(timestamp);

-- Trigger to update work_requests updated_at timestamp
CREATE OR REPLACE FUNCTION update_work_requests_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS work_requests_timestamp ON institution_work_requests;
CREATE TRIGGER work_requests_timestamp
BEFORE UPDATE ON institution_work_requests
FOR EACH ROW
EXECUTE FUNCTION update_work_requests_timestamp();
