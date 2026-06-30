-- Migration 062: Runtime schema compatibility for active civilization services
-- Some civilization tables pre-existed before later migrations used
-- CREATE TABLE IF NOT EXISTS, so required columns were never added.

ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS institution_id VARCHAR(255);
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS objective TEXT;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS evidence_count INT DEFAULT 0;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS claim_count INT DEFAULT 0;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS child_evidence_count INT DEFAULT 0;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS goal_depth INT DEFAULT 0;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS goal_path TEXT;
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS rollup_status VARCHAR(100);

UPDATE autonomy_goals
SET objective = COALESCE(objective, title, description),
    institution_id = COALESCE(institution_id, owning_institution_id::TEXT),
    updated_at = COALESCE(updated_at, created_at)
WHERE objective IS NULL OR institution_id IS NULL OR updated_at IS NULL;

ALTER TABLE departments ADD COLUMN IF NOT EXISTS entity_type VARCHAR(50) DEFAULT 'department';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS parent_id VARCHAR(255);
ALTER TABLE departments ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE departments ADD COLUMN IF NOT EXISTS purpose TEXT;
ALTER TABLE departments ADD COLUMN IF NOT EXISTS authority_scope JSONB DEFAULT '[]';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';
ALTER TABLE departments ADD COLUMN IF NOT EXISTS reputation_score NUMERIC(5, 2) DEFAULT 0.5;

UPDATE departments
SET entity_type = COALESCE(entity_type, 'department'),
    parent_id = COALESCE(parent_id, institution_id),
    purpose = COALESCE(purpose, description),
    authority_scope = COALESCE(authority_scope, '[]'::JSONB),
    metadata = COALESCE(metadata, '{}'::JSONB);

ALTER TABLE institutions ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE departments ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE departments ALTER COLUMN institution_id TYPE VARCHAR(255);
ALTER TABLE departments ALTER COLUMN parent_id TYPE VARCHAR(255);
ALTER TABLE institution_work_requests ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE specialist_allocation_history ALTER COLUMN work_request_id TYPE VARCHAR(255);
ALTER TABLE specialist_allocation_history ALTER COLUMN department_id TYPE VARCHAR(255);
ALTER TABLE load_test_results ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE load_test_results ALTER COLUMN scenario_id TYPE VARCHAR(255);
ALTER TABLE cutover_checklist ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE production_metrics ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE deployment_events ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE disaster_recovery_snapshots ALTER COLUMN id TYPE VARCHAR(255);
ALTER TABLE backup_recovery_log ALTER COLUMN id TYPE VARCHAR(255);

ALTER TABLE evidence_deduplication_map DROP CONSTRAINT IF EXISTS fk_source;
ALTER TABLE evidence_deduplication_map DROP CONSTRAINT IF EXISTS fk_canonical;
ALTER TABLE evidence_deduplication_map ALTER COLUMN evidence_source_id TYPE TEXT USING evidence_source_id::TEXT;
ALTER TABLE evidence_deduplication_map ALTER COLUMN canonical_evidence_id TYPE TEXT USING canonical_evidence_id::TEXT;

ALTER TABLE cross_institutional_evidence_access DROP CONSTRAINT IF EXISTS fk_evidence;
ALTER TABLE cross_institutional_evidence_access ALTER COLUMN evidence_id TYPE TEXT USING evidence_id::TEXT;
ALTER TABLE cross_institutional_evidence_access ALTER COLUMN source_institution_id TYPE VARCHAR(255);
ALTER TABLE cross_institutional_evidence_access ALTER COLUMN requesting_institution_id TYPE VARCHAR(255);

ALTER TABLE entity_reputation_audit_log ADD COLUMN IF NOT EXISTS institution_id VARCHAR(255);
ALTER TABLE entity_reputation_audit_log ADD COLUMN IF NOT EXISTS old_reputation NUMERIC(5, 2);
ALTER TABLE entity_reputation_audit_log ADD COLUMN IF NOT EXISTS reason TEXT;
ALTER TABLE institutions ADD COLUMN IF NOT EXISTS reputation_score NUMERIC(5, 2) DEFAULT 0.5;

ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS id VARCHAR(255);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS entity_type VARCHAR(100);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS previous_reputation NUMERIC(5, 2) DEFAULT 0.5;
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS new_reputation NUMERIC(5, 2);
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS change_reason TEXT;
ALTER TABLE reputation_audit_log ADD COLUMN IF NOT EXISTS audit_timestamp TIMESTAMP DEFAULT NOW();

UPDATE entity_reputation_audit_log
SET old_reputation = COALESCE(old_reputation, previous_reputation),
    reason = COALESCE(reason, change_reason);

CREATE OR REPLACE FUNCTION set_department_institution_id_from_parent()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.institution_id IS NULL THEN
    NEW.institution_id := NEW.parent_id;
  END IF;
  IF NEW.parent_id IS NULL THEN
    NEW.parent_id := NEW.institution_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_departments_set_institution_id ON departments;
CREATE TRIGGER trg_departments_set_institution_id
BEFORE INSERT OR UPDATE ON departments
FOR EACH ROW
EXECUTE FUNCTION set_department_institution_id_from_parent();

ALTER TABLE cross_institutional_evidence_access DROP CONSTRAINT IF EXISTS fk_source_inst;
ALTER TABLE cross_institutional_evidence_access DROP CONSTRAINT IF EXISTS fk_requesting_inst;
ALTER TABLE cross_institutional_evidence_access
  ADD CONSTRAINT fk_source_inst
  FOREIGN KEY (source_institution_id) REFERENCES institutions(id) ON DELETE CASCADE NOT VALID;
ALTER TABLE cross_institutional_evidence_access
  ADD CONSTRAINT fk_requesting_inst
  FOREIGN KEY (requesting_institution_id) REFERENCES institutions(id) ON DELETE CASCADE NOT VALID;
