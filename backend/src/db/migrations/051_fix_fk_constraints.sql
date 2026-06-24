-- Migration 051: Fix Foreign Key Constraints
-- Purpose: Fix FK constraint references to use correct column and type
-- The action_id columns should store VARCHAR from ActionSpec.actionId

-- Drop existing FK constraints that reference wrong table/types
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_action' AND table_name = 'autonomy_evidence') THEN
    ALTER TABLE autonomy_evidence DROP CONSTRAINT fk_action;
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_action' AND table_name = 'autonomy_claims') THEN
    ALTER TABLE autonomy_claims DROP CONSTRAINT fk_action;
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_action' AND table_name = 'autonomy_searches') THEN
    ALTER TABLE autonomy_searches DROP CONSTRAINT fk_action;
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_action' AND table_name = 'autonomy_memory') THEN
    ALTER TABLE autonomy_memory DROP CONSTRAINT fk_action;
  END IF;
END $$;

-- Step 1: Convert action_id columns from UUID to VARCHAR(36) using USING clause for type casting
ALTER TABLE IF EXISTS autonomy_evidence
ALTER COLUMN action_id TYPE VARCHAR(36) USING (CASE WHEN action_id IS NOT NULL THEN action_id::text ELSE NULL END);

ALTER TABLE IF EXISTS autonomy_claims
ALTER COLUMN action_id TYPE VARCHAR(36) USING (CASE WHEN action_id IS NOT NULL THEN action_id::text ELSE NULL END);

ALTER TABLE IF EXISTS autonomy_searches
ALTER COLUMN action_id TYPE VARCHAR(36) USING (CASE WHEN action_id IS NOT NULL THEN action_id::text ELSE NULL END);

ALTER TABLE IF EXISTS autonomy_memory
ALTER COLUMN action_id TYPE VARCHAR(36) USING (CASE WHEN action_id IS NOT NULL THEN action_id::text ELSE NULL END);

-- Step 2: Create NEW FK constraints with unique names to avoid naming conflicts
ALTER TABLE autonomy_evidence
ADD CONSTRAINT fk_evidence_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_claims
ADD CONSTRAINT fk_claims_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_searches
ADD CONSTRAINT fk_searches_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_memory
ADD CONSTRAINT fk_memory_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;
