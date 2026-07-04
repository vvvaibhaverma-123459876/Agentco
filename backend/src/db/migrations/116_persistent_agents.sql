-- Migration 116: persistent agent identity (GA6).
--
-- Spawned specialists used a fresh uuid per spawn, so a "society" member had
-- no identity, memory, or trust that survived process death. This table gives
-- each role a STABLE agent id. Re-spawning the same role reattaches to the
-- same record, so its per-agent memory (agent_memories.agent_id) and its
-- calibration/trust (trust_scores.subject_id) accumulate across runs.

CREATE TABLE IF NOT EXISTS persistent_agents (
  agent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role TEXT NOT NULL UNIQUE,
  memory_namespace TEXT NOT NULL,
  spawn_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_spawned_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_persistent_agents_role ON persistent_agents(role);
