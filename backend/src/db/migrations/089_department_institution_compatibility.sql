-- Migration 089: Department institution compatibility
--
-- Older local databases may have a departments table created before the
-- civilization institution contract was formalized. Runtime services require
-- departments.institution_id for work routing and allocation decisions, while
-- some legacy tests and scripts still populate parent_id. Keep the repair
-- additive and let the existing trigger mirror parent_id/institution_id.

ALTER TABLE departments ADD COLUMN IF NOT EXISTS institution_id VARCHAR(255);

UPDATE departments
SET institution_id = parent_id
WHERE institution_id IS NULL
  AND parent_id IS NOT NULL;

UPDATE departments
SET parent_id = institution_id
WHERE parent_id IS NULL
  AND institution_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_departments_institution_id ON departments(institution_id);

ALTER TABLE departments ALTER COLUMN institution_id SET DEFAULT NULL;
