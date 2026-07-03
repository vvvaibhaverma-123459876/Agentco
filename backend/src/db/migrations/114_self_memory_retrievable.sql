-- Migration 114: make autonomous self-memory retrievable (GA1).
--
-- The autonomy loop's UPDATE_MEMORY action wrote only `autonomy_memory`, which
-- the planner's memory-retrieval path (agent_memories) never reads. From now
-- on handleUpdateMemory dual-writes into agent_memories as a self-derived
-- HYPOTHESIS (episodic, namespace 'autonomous_self', importance 0.4). This
-- migration backfills EXISTING autonomy_memory rows the same way so past
-- self-memories also become retrievable, without dropping or mutating the
-- canonical autonomy_memory rows.
--
-- Idempotent: agent_memories.task_id holds the source autonomy_memory id, so a
-- row is only mirrored once. Reversible: DELETE ... WHERE namespace =
-- 'autonomous_self' removes exactly the mirrored rows.

INSERT INTO agent_memories
  (agent_id, memory_type, namespace, task_id, domain, summary, content, importance, created_at)
SELECT
  'autonomy-loop',
  'episodic',
  'autonomous_self',
  am.id::text,
  g.domain,
  LEFT(COALESCE(NULLIF(am.content->>'text', ''), am.content::text), 2000),
  jsonb_build_object(
    'source', 'autonomous_update_memory_backfill',
    'action_id', am.action_id,
    'autonomy_memory_id', am.id,
    'original', am.content
  ),
  0.4,
  am.created_at
FROM autonomy_memory am
LEFT JOIN autonomy_goal_actions a ON a.action_id = am.action_id
LEFT JOIN autonomy_goals g ON g.id = a.goal_id
WHERE COALESCE(NULLIF(am.content->>'text', ''), am.content::text) IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM agent_memories mem
     WHERE mem.namespace = 'autonomous_self'
       AND mem.task_id = am.id::text
  );
