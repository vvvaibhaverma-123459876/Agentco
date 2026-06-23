-- Migration 055: Deadlock Prevention & Concurrency Control
-- Adds coordination mechanisms for safe concurrent goal execution
-- Date: 2026-06-23

-- Track active goal executions to detect circular dependencies
CREATE TABLE IF NOT EXISTS goal_execution_locks (
  id VARCHAR(36) PRIMARY KEY,
  goal_id VARCHAR(36) NOT NULL,
  institution_id VARCHAR(36) NOT NULL,
  acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  acquired_by VARCHAR(100),
  lock_type VARCHAR(50) DEFAULT 'exclusive',
  status VARCHAR(50) DEFAULT 'active',
  released_at TIMESTAMP,
  CONSTRAINT fk_goal FOREIGN KEY (goal_id) REFERENCES autonomy_goals(id),
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_exec_locks_goal ON goal_execution_locks(goal_id);
CREATE INDEX IF NOT EXISTS idx_exec_locks_institution ON goal_execution_locks(institution_id);
CREATE INDEX IF NOT EXISTS idx_exec_locks_status ON goal_execution_locks(status);

-- Detect circular dependencies between goals
CREATE TABLE IF NOT EXISTS goal_dependency_graph (
  id VARCHAR(36) PRIMARY KEY,
  source_goal_id VARCHAR(36) NOT NULL,
  target_goal_id VARCHAR(36) NOT NULL,
  dependency_type VARCHAR(100),
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_source FOREIGN KEY (source_goal_id) REFERENCES autonomy_goals(id),
  CONSTRAINT fk_target FOREIGN KEY (target_goal_id) REFERENCES autonomy_goals(id)
);

CREATE INDEX IF NOT EXISTS idx_dep_source ON goal_dependency_graph(source_goal_id);
CREATE INDEX IF NOT EXISTS idx_dep_target ON goal_dependency_graph(target_goal_id);

-- Track deadlock incidents for monitoring
CREATE TABLE IF NOT EXISTS deadlock_incidents (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  goal_ids JSONB NOT NULL,
  circular_path TEXT,
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolution_status VARCHAR(50) DEFAULT 'detected',
  resolved_at TIMESTAMP,
  resolution_method VARCHAR(100),
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_deadlock_institution ON deadlock_incidents(institution_id);
CREATE INDEX IF NOT EXISTS idx_deadlock_status ON deadlock_incidents(resolution_status);

-- Long-term consistency verification
CREATE TABLE IF NOT EXISTS consistency_checks (
  id VARCHAR(36) PRIMARY KEY,
  check_type VARCHAR(100),
  institution_id VARCHAR(36),
  goal_id VARCHAR(36),
  inconsistency_found BOOLEAN DEFAULT FALSE,
  details JSONB,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id),
  CONSTRAINT fk_goal FOREIGN KEY (goal_id) REFERENCES autonomy_goals(id)
);

CREATE INDEX IF NOT EXISTS idx_consistency_type ON consistency_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_consistency_institution ON consistency_checks(institution_id);
CREATE INDEX IF NOT EXISTS idx_consistency_goal ON consistency_checks(goal_id);

-- Reputation audit trail for dispute resolution
CREATE TABLE IF NOT EXISTS reputation_audit_log (
  id VARCHAR(36) PRIMARY KEY,
  entity_id VARCHAR(36) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  previous_reputation NUMERIC(5, 2),
  new_reputation NUMERIC(5, 2),
  change_reason TEXT,
  audit_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  auditor_id VARCHAR(36),
  dispute_status VARCHAR(50) DEFAULT 'finalized'
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON reputation_audit_log(entity_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON reputation_audit_log(audit_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_dispute ON reputation_audit_log(dispute_status);

-- Governance decision constraints at scale
CREATE TABLE IF NOT EXISTS governance_constraint_violations (
  id VARCHAR(36) PRIMARY KEY,
  institution_id VARCHAR(36) NOT NULL,
  violation_type VARCHAR(100),
  decision_id VARCHAR(36),
  violating_action TEXT,
  severity VARCHAR(50) DEFAULT 'medium',
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution TEXT,
  CONSTRAINT fk_institution FOREIGN KEY (institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_violation_institution ON governance_constraint_violations(institution_id);
CREATE INDEX IF NOT EXISTS idx_violation_type ON governance_constraint_violations(violation_type);
CREATE INDEX IF NOT EXISTS idx_violation_severity ON governance_constraint_violations(severity);

-- Function to detect circular dependencies in goal graph
CREATE OR REPLACE FUNCTION detect_circular_dependencies(p_institution_id VARCHAR(36))
RETURNS TABLE(has_cycle BOOLEAN, goal_cycle TEXT) AS $$
DECLARE
  v_cycle TEXT;
BEGIN
  -- Simplified cycle detection (in production, would use full DFS)
  -- Check if any goal's parent is also its ancestor
  WITH RECURSIVE goal_tree AS (
    SELECT id, parent_goal_id, id::TEXT as path
    FROM autonomy_goals
    WHERE institution_id = p_institution_id AND parent_goal_id IS NULL

    UNION ALL

    SELECT ag.id, ag.parent_goal_id, gt.path || ',' || ag.id::TEXT
    FROM autonomy_goals ag
    JOIN goal_tree gt ON ag.parent_goal_id = gt.id
    WHERE ag.institution_id = p_institution_id AND gt.path NOT LIKE '%' || ag.id::TEXT || '%'
  )
  SELECT
    CASE WHEN COUNT(*) > 0 THEN TRUE ELSE FALSE END,
    STRING_AGG(path, ' | ')
  INTO has_cycle, goal_cycle
  FROM goal_tree
  WHERE path LIKE '%' || id::TEXT || '%';

  RETURN QUERY SELECT has_cycle, goal_cycle;
END;
$$ LANGUAGE plpgsql;

-- Function to acquire goal execution lock (non-blocking)
CREATE OR REPLACE FUNCTION acquire_goal_lock(p_goal_id VARCHAR(36), p_institution_id VARCHAR(36), p_acquired_by VARCHAR(100))
RETURNS TABLE(lock_id VARCHAR(36), acquired BOOLEAN) AS $$
DECLARE
  v_lock_id VARCHAR(36);
  v_existing_lock VARCHAR(36);
BEGIN
  -- Check if lock already exists
  SELECT id INTO v_existing_lock
  FROM goal_execution_locks
  WHERE goal_id = p_goal_id AND status = 'active'
  LIMIT 1;

  IF v_existing_lock IS NOT NULL THEN
    RETURN QUERY SELECT v_existing_lock, FALSE;
    RETURN;
  END IF;

  -- Create new lock
  v_lock_id := uuid_generate_v4()::VARCHAR(36);
  INSERT INTO goal_execution_locks (id, goal_id, institution_id, acquired_by, status)
  VALUES (v_lock_id, p_goal_id, p_institution_id, p_acquired_by, 'active');

  RETURN QUERY SELECT v_lock_id, TRUE;
END;
$$ LANGUAGE plpgsql;

-- Function to release goal execution lock
CREATE OR REPLACE FUNCTION release_goal_lock(p_lock_id VARCHAR(36))
RETURNS TABLE(released BOOLEAN) AS $$
BEGIN
  UPDATE goal_execution_locks
  SET status = 'released', released_at = CURRENT_TIMESTAMP
  WHERE id = p_lock_id AND status = 'active';

  RETURN QUERY SELECT FOUND;
END;
$$ LANGUAGE plpgsql;

-- Trigger to log reputation changes for audit
CREATE OR REPLACE FUNCTION log_reputation_change()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.reputation_score IS DISTINCT FROM OLD.reputation_score THEN
    INSERT INTO reputation_audit_log
      (id, entity_id, entity_type, previous_reputation, new_reputation,
       change_reason, audit_timestamp)
    VALUES
      (uuid_generate_v4()::VARCHAR(36), NEW.id, TG_TABLE_NAME,
       OLD.reputation_score, NEW.reputation_score,
       'automated_update', CURRENT_TIMESTAMP);
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_reputation_change ON institutions;
CREATE TRIGGER audit_reputation_change
AFTER UPDATE ON institutions
FOR EACH ROW
EXECUTE FUNCTION log_reputation_change();

DROP TRIGGER IF EXISTS audit_reputation_change_dept ON departments;
CREATE TRIGGER audit_reputation_change_dept
AFTER UPDATE ON departments
FOR EACH ROW
EXECUTE FUNCTION log_reputation_change();
