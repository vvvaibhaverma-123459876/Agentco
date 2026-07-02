-- Migration 056: Production Deployment Infrastructure
-- Adds load test tracking, failure recovery, and production monitoring
-- Date: 2026-06-23

-- Track load test executions and results
CREATE TABLE IF NOT EXISTS load_test_results (
  id VARCHAR(36) PRIMARY KEY,
  scenario_id VARCHAR(36) NOT NULL,
  scenario_name VARCHAR(255),
  institutions_created INT,
  work_requests_submitted INT,
  goals_completed INT,
  total_duration_seconds INT,
  avg_response_time_ms NUMERIC,
  p99_response_time_ms NUMERIC,
  errors_encountered INT DEFAULT 0,
  deadlock_incidents INT DEFAULT 0,
  consistency_violations INT DEFAULT 0,
  reputation_anomalies INT DEFAULT 0,
  status VARCHAR(50) DEFAULT 'passed',
  test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_load_test_scenario ON load_test_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_load_test_status ON load_test_results(status);
CREATE INDEX IF NOT EXISTS idx_load_test_timestamp ON load_test_results(test_timestamp);

-- Track failure recovery incidents
CREATE TABLE IF NOT EXISTS failure_recovery_incidents (
  id VARCHAR(36) PRIMARY KEY,
  failure_type VARCHAR(100),
  severity VARCHAR(50),
  affected_institution_id VARCHAR(36),
  affected_goal_ids JSONB DEFAULT '[]',
  description TEXT,
  root_cause TEXT,
  recovery_action TEXT,
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  recovered_at TIMESTAMP,
  data_integrity_verified BOOLEAN DEFAULT FALSE,
  CONSTRAINT fk_institution FOREIGN KEY (affected_institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_failure_type ON failure_recovery_incidents(failure_type);
CREATE INDEX IF NOT EXISTS idx_failure_severity ON failure_recovery_incidents(severity);
CREATE INDEX IF NOT EXISTS idx_failure_institution ON failure_recovery_incidents(affected_institution_id);

-- Monitor production health metrics
CREATE TABLE IF NOT EXISTS production_metrics (
  id VARCHAR(36) PRIMARY KEY,
  metric_type VARCHAR(100),
  metric_name VARCHAR(255),
  metric_value NUMERIC,
  institution_id VARCHAR(36),
  measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_metrics_type ON production_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON production_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_institution ON production_metrics(institution_id);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON production_metrics(measured_at);

-- Track deployment events
CREATE TABLE IF NOT EXISTS deployment_events (
  id VARCHAR(36) PRIMARY KEY,
  deployment_id VARCHAR(36),
  event_type VARCHAR(100),
  event_status VARCHAR(50),
  event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  details JSONB,
  affected_institutions INT DEFAULT 0,
  rollback_available BOOLEAN DEFAULT TRUE,
  completed_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_deployment_id ON deployment_events(deployment_id);
CREATE INDEX IF NOT EXISTS idx_deployment_event_type ON deployment_events(event_type);
CREATE INDEX IF NOT EXISTS idx_deployment_status ON deployment_events(event_status);

-- Disaster recovery state snapshots
CREATE TABLE IF NOT EXISTS disaster_recovery_snapshots (
  id VARCHAR(36) PRIMARY KEY,
  snapshot_type VARCHAR(100),
  snapshot_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  institution_count INT,
  goal_count INT,
  specialist_count INT,
  total_reputation_sum NUMERIC,
  data_integrity_status VARCHAR(50),
  snapshot_location TEXT,
  verified_recoverable BOOLEAN DEFAULT FALSE,
  recovery_tested_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_snapshot_type ON disaster_recovery_snapshots(snapshot_type);
CREATE INDEX IF NOT EXISTS idx_snapshot_timestamp ON disaster_recovery_snapshots(snapshot_timestamp);

-- Production cutover checklist
CREATE TABLE IF NOT EXISTS cutover_checklist (
  id VARCHAR(36) PRIMARY KEY,
  checklist_item VARCHAR(255),
  status VARCHAR(50) DEFAULT 'pending',
  checked_by VARCHAR(255),
  checked_at TIMESTAMP,
  verification_notes TEXT,
  blocking BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_cutover_status ON cutover_checklist(status);
CREATE INDEX IF NOT EXISTS idx_cutover_blocking ON cutover_checklist(blocking);

-- Backup and recovery log
CREATE TABLE IF NOT EXISTS backup_recovery_log (
  id VARCHAR(36) PRIMARY KEY,
  backup_id VARCHAR(36),
  backup_type VARCHAR(100),
  backup_timestamp TIMESTAMP,
  backup_location TEXT,
  size_bytes BIGINT,
  integrity_hash VARCHAR(255),
  recovery_tested BOOLEAN DEFAULT FALSE,
  recovery_timestamp TIMESTAMP,
  success BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_backup_id ON backup_recovery_log(backup_id);
CREATE INDEX IF NOT EXISTS idx_backup_timestamp ON backup_recovery_log(backup_timestamp);

-- Create load_test_results table for load testing
CREATE TABLE IF NOT EXISTS load_test_results (
  id VARCHAR(36) PRIMARY KEY,
  scenario_id VARCHAR(36),
  scenario_name VARCHAR(255),
  institutions_created INT,
  work_requests_submitted INT,
  goals_completed INT,
  total_duration_seconds INT,
  avg_response_time_ms NUMERIC,
  p99_response_time_ms NUMERIC,
  errors_encountered INT DEFAULT 0,
  deadlock_incidents INT DEFAULT 0,
  consistency_violations INT DEFAULT 0,
  reputation_anomalies INT DEFAULT 0,
  status VARCHAR(50),
  test_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_load_scenario ON load_test_results(scenario_id);
CREATE INDEX IF NOT EXISTS idx_load_status ON load_test_results(status);

-- Function to record production metrics
CREATE OR REPLACE FUNCTION record_production_metric(
  p_metric_type VARCHAR(100),
  p_metric_name VARCHAR(255),
  p_metric_value NUMERIC,
  p_institution_id VARCHAR(36) DEFAULT NULL
)
RETURNS VARCHAR(36) AS $$
DECLARE
  v_metric_id VARCHAR(36);
BEGIN
  v_metric_id := gen_random_uuid()::VARCHAR(36);

  INSERT INTO production_metrics
    (id, metric_type, metric_name, metric_value, institution_id, measured_at)
  VALUES
    (v_metric_id, p_metric_type, p_metric_name, p_metric_value, p_institution_id, CURRENT_TIMESTAMP);

  RETURN v_metric_id;
END;
$$ LANGUAGE plpgsql;

-- Trigger to record metrics on goal completion
CREATE OR REPLACE FUNCTION record_goal_completion_metrics()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
    PERFORM record_production_metric(
      'goal_completion',
      'goals_completed_per_day',
      1,
      NEW.institution_id
    );
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_goal_metrics ON autonomy_goals;
CREATE TRIGGER trigger_goal_metrics
AFTER UPDATE ON autonomy_goals
FOR EACH ROW
EXECUTE FUNCTION record_goal_completion_metrics();
