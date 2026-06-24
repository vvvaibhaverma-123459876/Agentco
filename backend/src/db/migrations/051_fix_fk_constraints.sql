-- Migration 051: Fix Foreign Key Constraints
-- Purpose: Fix FK references to use autonomy_goal_actions.action_id (VARCHAR)
-- The action_id column stores the VARCHAR action ID from ActionSpec, not the UUID primary key

-- Drop existing constraints that reference the wrong column
ALTER TABLE IF EXISTS autonomy_evidence
DROP CONSTRAINT IF EXISTS fk_action CASCADE;

ALTER TABLE IF EXISTS autonomy_claims
DROP CONSTRAINT IF EXISTS fk_action CASCADE;

ALTER TABLE IF EXISTS autonomy_searches
DROP CONSTRAINT IF EXISTS fk_action CASCADE;

ALTER TABLE IF EXISTS autonomy_memory
DROP CONSTRAINT IF EXISTS fk_action CASCADE;

-- Re-add constraints with correct column references
ALTER TABLE autonomy_evidence
ADD CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_claims
ADD CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_searches
ADD CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;

ALTER TABLE autonomy_memory
ADD CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_goal_actions(action_id) ON DELETE CASCADE;
