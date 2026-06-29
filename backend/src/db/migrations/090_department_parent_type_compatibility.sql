-- Migration 090: Department parent/institution type compatibility
--
-- Some pre-civilization local schemas created departments.parent_id as TEXT
-- and later compatibility added institution_id as VARCHAR. Runtime inserts use
-- the same bound value for both columns, so their types must agree.

ALTER TABLE departments ALTER COLUMN institution_id TYPE TEXT USING institution_id::TEXT;
ALTER TABLE departments ALTER COLUMN parent_id TYPE TEXT USING parent_id::TEXT;

UPDATE departments
SET institution_id = parent_id
WHERE institution_id IS NULL
  AND parent_id IS NOT NULL;

UPDATE departments
SET parent_id = institution_id
WHERE parent_id IS NULL
  AND institution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_departments_institution_id ON departments(institution_id);
