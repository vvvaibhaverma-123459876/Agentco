-- Migration 078: Agent membership service compatibility.
--
-- civilization.services.institution_service.add_agent_to_department reads an
-- id column for existing memberships, while the current table uses
-- (agent_id, department_id) as the primary key. Add a stable surrogate id
-- without weakening the existing composite primary key.

ALTER TABLE agent_membership_edges
  ADD COLUMN IF NOT EXISTS id UUID DEFAULT gen_random_uuid();

UPDATE agent_membership_edges
   SET id = gen_random_uuid()
 WHERE id IS NULL;

ALTER TABLE agent_membership_edges
  ALTER COLUMN id SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_agent_membership_edges_id
  ON agent_membership_edges(id);
