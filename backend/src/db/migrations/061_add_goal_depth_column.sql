-- Migration 061: Add goal depth tracking for hierarchy
-- Purpose: Track goal nesting depth for spawn_specialist constraints

-- Add depth column to autonomy_goals
ALTER TABLE autonomy_goals ADD COLUMN IF NOT EXISTS depth INTEGER DEFAULT 0;

-- Update depth based on parent_goal_id hierarchy
UPDATE autonomy_goals
SET depth = 1
WHERE parent_goal_id IS NOT NULL AND depth = 0;

-- For deeper hierarchies, recursively compute
WITH RECURSIVE goal_depth AS (
  -- Base case: top-level goals
  SELECT id, 0 AS computed_depth
  FROM autonomy_goals
  WHERE parent_goal_id IS NULL

  UNION ALL

  -- Recursive case: child goals
  SELECT g.id, gd.computed_depth + 1
  FROM autonomy_goals g
  JOIN goal_depth gd ON g.parent_goal_id = gd.id
)
UPDATE autonomy_goals ag
SET depth = gd.computed_depth
FROM goal_depth gd
WHERE ag.id = gd.id AND ag.depth != gd.computed_depth;

-- Create index for depth queries
CREATE INDEX IF NOT EXISTS idx_autonomy_goals_depth ON autonomy_goals(depth);

-- Add constraint: max depth is 2 (enforced in application logic)
ALTER TABLE autonomy_goals ADD CONSTRAINT depth_limit CHECK (depth <= 2);
