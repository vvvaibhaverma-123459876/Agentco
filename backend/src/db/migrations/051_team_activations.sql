-- Migration 051: Team Activations Table for Multi-Agent Orchestration
-- Tracks specialist agent instances spawned by the autonomy orchestrator

CREATE TABLE IF NOT EXISTS autonomy_team_activations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_goal_id UUID NOT NULL,
  specialist_id VARCHAR(36) UNIQUE,
  specialist_role VARCHAR(50) NOT NULL,
  objective TEXT NOT NULL,
  budget_tokens INT DEFAULT 0,
  budget_iterations INT DEFAULT 0,
  budget_seconds INT DEFAULT 0,
  tokens_used INT DEFAULT 0,
  iterations_used INT DEFAULT 0,
  status VARCHAR(50) DEFAULT 'active',  -- active, completed, failed, timeout, budget_exceeded
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  results JSONB,  -- { artifacts: [], evidence: [], claims: [] }
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT fk_parent_goal FOREIGN KEY (parent_goal_id) REFERENCES autonomy_goals(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_team_activations_parent ON autonomy_team_activations(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_team_activations_status ON autonomy_team_activations(status);
CREATE INDEX IF NOT EXISTS idx_team_activations_specialist ON autonomy_team_activations(specialist_id);
CREATE INDEX IF NOT EXISTS idx_team_activations_role ON autonomy_team_activations(specialist_role);
