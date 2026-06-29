-- Migration 091: Restore department institution mirror trigger
--
-- Some migration orders left departments without the trigger that mirrors
-- parent_id and institution_id. Work-routing code depends on institution_id
-- being populated even when legacy callers insert only parent_id.

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

UPDATE departments
SET institution_id = parent_id
WHERE institution_id IS NULL
  AND parent_id IS NOT NULL;
