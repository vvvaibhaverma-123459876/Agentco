-- Migration 063: Follow-up compatibility for databases that already applied 062

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

ALTER TABLE departments ADD COLUMN IF NOT EXISTS reputation_score NUMERIC(5, 2) DEFAULT 0.5;

ALTER TABLE cross_institutional_evidence_access DROP CONSTRAINT IF EXISTS fk_source_inst;
ALTER TABLE cross_institutional_evidence_access DROP CONSTRAINT IF EXISTS fk_requesting_inst;
ALTER TABLE cross_institutional_evidence_access
  ADD CONSTRAINT fk_source_inst
  FOREIGN KEY (source_institution_id) REFERENCES institutions(id) ON DELETE CASCADE NOT VALID;
ALTER TABLE cross_institutional_evidence_access
  ADD CONSTRAINT fk_requesting_inst
  FOREIGN KEY (requesting_institution_id) REFERENCES institutions(id) ON DELETE CASCADE NOT VALID;
