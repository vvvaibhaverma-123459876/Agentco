-- Migration 054: Goal Hierarchies for Long-Term Coordination
-- Enables multi-level goal planning with parent-child relationships
-- Date: 2026-06-23

-- Enhanced autonomy_goals with hierarchy support
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS parent_goal_id VARCHAR(36);
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS goal_depth INT DEFAULT 0;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS goal_path TEXT;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS rollup_status VARCHAR(100);
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS child_evidence_count INT DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_goals_parent ON autonomy_goals(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_goals_depth ON autonomy_goals(goal_depth);
CREATE INDEX IF NOT EXISTS idx_goals_path ON autonomy_goals(goal_path);

-- Track evidence deduplication across institutions
CREATE TABLE IF NOT EXISTS evidence_deduplication_map (
  id VARCHAR(36) PRIMARY KEY,
  evidence_source_id VARCHAR(36) NOT NULL,
  canonical_evidence_id VARCHAR(36) NOT NULL,
  institution_ids JSONB DEFAULT '[]',
  work_request_ids JSONB DEFAULT '[]',
  confidence_score NUMERIC(3, 2),
  first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  last_verified TIMESTAMP,
  is_active BOOLEAN DEFAULT TRUE,
  CONSTRAINT fk_source FOREIGN KEY (evidence_source_id) REFERENCES autonomy_evidence(id),
  CONSTRAINT fk_canonical FOREIGN KEY (canonical_evidence_id) REFERENCES autonomy_evidence(id)
);

CREATE INDEX IF NOT EXISTS idx_dedup_source ON evidence_deduplication_map(evidence_source_id);
CREATE INDEX IF NOT EXISTS idx_dedup_canonical ON evidence_deduplication_map(canonical_evidence_id);
CREATE INDEX IF NOT EXISTS idx_dedup_active ON evidence_deduplication_map(is_active);

-- Track cross-institutional evidence sharing
CREATE TABLE IF NOT EXISTS cross_institutional_evidence_access (
  id VARCHAR(36) PRIMARY KEY,
  evidence_id VARCHAR(36) NOT NULL,
  source_institution_id VARCHAR(36) NOT NULL,
  requesting_institution_id VARCHAR(36) NOT NULL,
  access_status VARCHAR(50) DEFAULT 'pending',
  verification_status VARCHAR(50) DEFAULT 'unverified',
  agreement_type VARCHAR(100),
  accessed_at TIMESTAMP,
  verified_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_evidence FOREIGN KEY (evidence_id) REFERENCES autonomy_evidence(id),
  CONSTRAINT fk_source_inst FOREIGN KEY (source_institution_id) REFERENCES institutions(id),
  CONSTRAINT fk_requesting_inst FOREIGN KEY (requesting_institution_id) REFERENCES institutions(id)
);

CREATE INDEX IF NOT EXISTS idx_access_evidence ON cross_institutional_evidence_access(evidence_id);
CREATE INDEX IF NOT EXISTS idx_access_source_inst ON cross_institutional_evidence_access(source_institution_id);
CREATE INDEX IF NOT EXISTS idx_access_requesting_inst ON cross_institutional_evidence_access(requesting_institution_id);
CREATE INDEX IF NOT EXISTS idx_access_status ON cross_institutional_evidence_access(access_status);

-- Track specialist allocation decisions for adaptation
CREATE TABLE IF NOT EXISTS specialist_allocation_history (
  id VARCHAR(36) PRIMARY KEY,
  work_request_id VARCHAR(36) NOT NULL,
  department_id VARCHAR(36) NOT NULL,
  specialist_role VARCHAR(100) NOT NULL,
  allocated_reputation NUMERIC(5, 2),
  actual_performance NUMERIC(5, 2),
  allocation_reasoning TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_work_request FOREIGN KEY (work_request_id) REFERENCES institution_work_requests(id),
  CONSTRAINT fk_department FOREIGN KEY (department_id) REFERENCES departments(id)
);

CREATE INDEX IF NOT EXISTS idx_alloc_work_request ON specialist_allocation_history(work_request_id);
CREATE INDEX IF NOT EXISTS idx_alloc_department ON specialist_allocation_history(department_id);
CREATE INDEX IF NOT EXISTS idx_alloc_specialist ON specialist_allocation_history(specialist_role);

-- Goal rollup: track aggregated results from child goals
CREATE TABLE IF NOT EXISTS goal_rollup_results (
  id VARCHAR(36) PRIMARY KEY,
  parent_goal_id VARCHAR(36) NOT NULL,
  child_goal_ids JSONB DEFAULT '[]',
  total_evidence_count INT DEFAULT 0,
  total_claim_count INT DEFAULT 0,
  evidence_quality_avg NUMERIC(3, 2),
  claim_accuracy_avg NUMERIC(3, 2),
  rollup_completeness NUMERIC(3, 2),
  computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_parent_goal FOREIGN KEY (parent_goal_id) REFERENCES autonomy_goals(id)
);

CREATE INDEX IF NOT EXISTS idx_rollup_parent ON goal_rollup_results(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_rollup_completeness ON goal_rollup_results(rollup_completeness);

-- Track specialist team compositions for pattern learning
CREATE TABLE IF NOT EXISTS specialist_team_patterns (
  id VARCHAR(36) PRIMARY KEY,
  team_composition JSONB NOT NULL,
  success_count INT DEFAULT 0,
  total_deployments INT DEFAULT 0,
  avg_performance NUMERIC(3, 2),
  last_used TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_team_pattern_performance ON specialist_team_patterns(avg_performance DESC);

-- Function to update goal rollup on child goal completion
CREATE OR REPLACE FUNCTION update_parent_goal_rollup()
RETURNS TRIGGER AS $$
DECLARE
  parent_id VARCHAR(36);
  parent_status VARCHAR(100);
BEGIN
  -- Get parent goal ID
  IF NEW.parent_goal_id IS NOT NULL THEN
    parent_id := NEW.parent_goal_id;

    -- Update parent goal evidence count
    UPDATE autonomy_goals
    SET child_evidence_count = child_evidence_count + 1
    WHERE id = parent_id;

    -- Check if all child goals completed
    SELECT COUNT(*)
    INTO parent_status
    FROM autonomy_goals
    WHERE parent_goal_id = parent_id AND status != 'completed';

    -- If all children done, mark parent as ready for rollup
    IF parent_status = 0 THEN
      UPDATE autonomy_goals
      SET rollup_status = 'ready_for_rollup'
      WHERE id = parent_id;
    END IF;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS goal_hierarchy_update ON autonomy_goals;
CREATE TRIGGER goal_hierarchy_update
AFTER UPDATE ON autonomy_goals
FOR EACH ROW
WHEN (NEW.status = 'completed')
EXECUTE FUNCTION update_parent_goal_rollup();
