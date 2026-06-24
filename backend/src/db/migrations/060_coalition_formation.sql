-- COALITION FORMATION SYSTEM
-- Team assembly using collaboration scores and specialization matching

-- Coalition formations for tasks
CREATE TABLE IF NOT EXISTS coalition_formations (
  coalition_id VARCHAR(36) PRIMARY KEY,
  task_id VARCHAR(36) NOT NULL,
  objective TEXT NOT NULL,
  required_specializations JSONB NOT NULL DEFAULT '[]',  -- array of specialization strings
  team_lead VARCHAR(36) NOT NULL,
  members JSONB NOT NULL DEFAULT '[]',  -- array of TeamMember objects
  formation_score NUMERIC(3, 2) NOT NULL,  -- 0-1, quality of team composition
  status VARCHAR(50) NOT NULL DEFAULT 'forming',  -- forming, active, completed, failed
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  CONSTRAINT fk_task FOREIGN KEY (task_id) REFERENCES autonomy_goals(id) ON DELETE SET NULL
);

-- Create indexes for coalition lookup
CREATE INDEX IF NOT EXISTS idx_coalition_task ON coalition_formations(task_id);
CREATE INDEX IF NOT EXISTS idx_coalition_lead ON coalition_formations(team_lead);
CREATE INDEX IF NOT EXISTS idx_coalition_status ON coalition_formations(status);
CREATE INDEX IF NOT EXISTS idx_coalition_score ON coalition_formations(formation_score);
CREATE INDEX IF NOT EXISTS idx_coalition_created ON coalition_formations(created_at);

-- Coalition performance history
CREATE TABLE IF NOT EXISTS coalition_performance (
  performance_id VARCHAR(36) PRIMARY KEY,
  coalition_id VARCHAR(36) NOT NULL,
  metric_type VARCHAR(50) NOT NULL,  -- efficiency, quality, cohesion, specialization_coverage
  metric_value NUMERIC(5, 3) NOT NULL,  -- 0-100 scale
  evaluated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  notes TEXT,
  CONSTRAINT fk_coalition FOREIGN KEY (coalition_id) REFERENCES coalition_formations(coalition_id) ON DELETE CASCADE
);

-- Create indexes for performance tracking
CREATE INDEX IF NOT EXISTS idx_perf_coalition ON coalition_performance(coalition_id);
CREATE INDEX IF NOT EXISTS idx_perf_metric ON coalition_performance(metric_type);
CREATE INDEX IF NOT EXISTS idx_perf_evaluated ON coalition_performance(evaluated_at);

-- Coalition member assignments
CREATE TABLE IF NOT EXISTS coalition_member_assignments (
  assignment_id VARCHAR(36) PRIMARY KEY,
  coalition_id VARCHAR(36) NOT NULL,
  agent_id VARCHAR(36) NOT NULL,
  role VARCHAR(50) NOT NULL,  -- team_lead, core_member, supporting_member
  specializations JSONB NOT NULL DEFAULT '[]',
  assigned_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,
  performance_rating NUMERIC(3, 2),  -- 0-1, how well they performed
  CONSTRAINT fk_coalition_member FOREIGN KEY (coalition_id) REFERENCES coalition_formations(coalition_id) ON DELETE CASCADE
);

-- Create indexes for member assignments
CREATE INDEX IF NOT EXISTS idx_member_coalition ON coalition_member_assignments(coalition_id);
CREATE INDEX IF NOT EXISTS idx_member_agent ON coalition_member_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_member_role ON coalition_member_assignments(role);
CREATE INDEX IF NOT EXISTS idx_member_assigned ON coalition_member_assignments(assigned_at);

-- Coalition collaboration events
CREATE TABLE IF NOT EXISTS coalition_collaboration_events (
  event_id VARCHAR(36) PRIMARY KEY,
  coalition_id VARCHAR(36) NOT NULL,
  event_type VARCHAR(50) NOT NULL,  -- coordination_success, coordination_failure, member_joined, member_left
  magnitude NUMERIC(3, 2),  -- -1.0 to 1.0, impact of event
  involved_agents JSONB NOT NULL DEFAULT '[]',  -- array of agent IDs
  context JSONB NOT NULL DEFAULT '{}',
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT fk_coalition_event FOREIGN KEY (coalition_id) REFERENCES coalition_formations(coalition_id) ON DELETE CASCADE
);

-- Create indexes for collaboration events
CREATE INDEX IF NOT EXISTS idx_collab_coalition ON coalition_collaboration_events(coalition_id);
CREATE INDEX IF NOT EXISTS idx_collab_type ON coalition_collaboration_events(event_type);
CREATE INDEX IF NOT EXISTS idx_collab_timestamp ON coalition_collaboration_events(timestamp);

-- Coalition composition recommendations
CREATE TABLE IF NOT EXISTS coalition_composition_recommendations (
  recommendation_id VARCHAR(36) PRIMARY KEY,
  task_objective TEXT NOT NULL,
  required_specializations JSONB NOT NULL,
  recommended_lead_id VARCHAR(36),
  recommended_team_size INT NOT NULL,
  predicted_success_rate NUMERIC(3, 2),
  reasoning TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for recommendations
CREATE INDEX IF NOT EXISTS idx_recommend_created ON coalition_composition_recommendations(created_at);
