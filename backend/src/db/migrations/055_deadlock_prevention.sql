-- Migration 055: Deadlock Prevention & Concurrency Control
-- Adds coordination mechanisms for safe concurrent goal execution
-- Date: 2026-06-23

-- Track active goal executions to detect circular dependencies
CREATE TABLE IF NOT EXISTS goal_execution_locks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  goal_id UUID NOT NULL,
  institution_id VARCHAR(36) NOT NULL,
  acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  acquired_by VARCHAR(100),
  lock_type VARCHAR(50) DEFAULT 'exclusive',
  status VARCHAR(50) DEFAULT 'active',
  released_at TIMESTAMP
);

-- Detect circular dependencies between goals
CREATE TABLE IF NOT EXISTS goal_dependency_graph (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_goal_id UUID NOT NULL,
  target_goal_id UUID NOT NULL,
  dependency_type VARCHAR(100),
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Track deadlock incidents for monitoring
CREATE TABLE IF NOT EXISTS deadlock_incidents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR(36) NOT NULL,
  goal_ids JSONB NOT NULL,
  circular_path TEXT,
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolution_status VARCHAR(50) DEFAULT 'detected',
  resolved_at TIMESTAMP,
  resolution_method VARCHAR(100)
);

-- Long-term consistency verification
CREATE TABLE IF NOT EXISTS consistency_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  check_type VARCHAR(100),
  institution_id VARCHAR(36),
  goal_id UUID,
  inconsistency_found BOOLEAN DEFAULT FALSE,
  details JSONB,
  checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note: reputation_audit_log is created in migration 057_reputation_learning.sql
-- with a more complete schema for the reputation learning system

-- Governance decision constraints at scale
CREATE TABLE IF NOT EXISTS governance_constraint_violations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institution_id VARCHAR(36) NOT NULL,
  violation_type VARCHAR(100),
  decision_id VARCHAR(36),
  violating_action TEXT,
  severity VARCHAR(50) DEFAULT 'medium',
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  resolved_at TIMESTAMP,
  resolution TEXT
);

-- Create indexes after all tables are defined
DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_exec_locks_goal ON goal_execution_locks(goal_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_exec_locks_institution ON goal_execution_locks(institution_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_exec_locks_status ON goal_execution_locks(status);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_dep_source ON goal_dependency_graph(source_goal_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_dep_target ON goal_dependency_graph(target_goal_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_deadlock_institution ON deadlock_incidents(institution_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_deadlock_status ON deadlock_incidents(resolution_status);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_consistency_type ON consistency_checks(check_type);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_consistency_institution ON consistency_checks(institution_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_consistency_goal ON consistency_checks(goal_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_violation_institution ON governance_constraint_violations(institution_id);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_violation_type ON governance_constraint_violations(violation_type);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;

DO $$
BEGIN
  CREATE INDEX IF NOT EXISTS idx_violation_severity ON governance_constraint_violations(severity);
  EXCEPTION WHEN OTHERS THEN NULL;
END $$;
