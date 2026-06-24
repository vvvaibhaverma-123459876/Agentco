-- ADAPTIVE STRATEGY SYSTEM
-- Tracks research strategies, search queries, and resource allocation

-- Search strategies per goal
CREATE TABLE IF NOT EXISTS adaptive_strategies (
  strategy_id VARCHAR(36) PRIMARY KEY,
  goal_id VARCHAR(36) NOT NULL,
  approach VARCHAR(50) NOT NULL,  -- multi_angle_research, depth_first, breadth_first, adaptive

  -- Query execution history (JSON array of SearchQuery objects)
  queries JSONB NOT NULL DEFAULT '[]',

  -- Budget allocation and usage (JSON object)
  budget_allocation JSONB NOT NULL,
  -- Format: {
  --   web_fetches: number,
  --   llm_calls: number,
  --   time_seconds: number,
  --   web_fetches_used: number,
  --   llm_calls_used: number,
  --   time_used_seconds: number
  -- }

  -- Strategy metrics (JSON object)
  metrics JSONB NOT NULL,
  -- Format: {
  --   total_claims: number,
  --   quality_score: 0-100,
  --   roi: number,
  --   diversity_score: 0-1,
  --   convergence: 0-1,
  --   efficiency: 0-1
  -- }

  -- Strategy status
  status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, pivot_needed, completed, abandoned

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for strategy lookup
CREATE INDEX IF NOT EXISTS idx_strategy_goal ON adaptive_strategies(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategy_status ON adaptive_strategies(status);
CREATE INDEX IF NOT EXISTS idx_strategy_updated ON adaptive_strategies(updated_at);

-- Search query history (denormalized for analytics)
CREATE TABLE IF NOT EXISTS search_query_history (
  query_id VARCHAR(36) PRIMARY KEY,
  strategy_id VARCHAR(36) NOT NULL,
  goal_id VARCHAR(36) NOT NULL,
  query_text VARCHAR(500) NOT NULL,

  -- Execution stats
  executed_count INT NOT NULL DEFAULT 0,
  successful_claims INT NOT NULL DEFAULT 0,
  claims_per_execution NUMERIC(5, 3) NOT NULL DEFAULT 0.0,

  -- Query source type
  source_type VARCHAR(50) NOT NULL DEFAULT 'web',  -- web, academic, news, technical

  -- Last execution timestamp
  last_executed TIMESTAMP,

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_strategy FOREIGN KEY (strategy_id) REFERENCES adaptive_strategies(strategy_id) ON DELETE CASCADE
);

-- Create indexes for query history
CREATE INDEX IF NOT EXISTS idx_query_strategy ON search_query_history(strategy_id);
CREATE INDEX IF NOT EXISTS idx_query_goal ON search_query_history(goal_id);
CREATE INDEX IF NOT EXISTS idx_query_source_type ON search_query_history(source_type);
CREATE INDEX IF NOT EXISTS idx_query_success ON search_query_history(successful_claims);

-- Task assignments from strategies
CREATE TABLE IF NOT EXISTS task_assignments (
  assignment_id VARCHAR(36) PRIMARY KEY,
  strategy_id VARCHAR(36) NOT NULL,
  agent_id VARCHAR(36) NOT NULL,
  task_type VARCHAR(50) NOT NULL,  -- search, fetch, analyze, synthesize, validate
  focus_area VARCHAR(500) NOT NULL,
  estimated_duration INT NOT NULL,

  -- Required specialization (JSON array)
  required_specialization JSONB NOT NULL DEFAULT '[]',

  -- Priority level
  priority VARCHAR(20) NOT NULL DEFAULT 'medium',  -- high, medium, low

  -- Status and results
  status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, executing, completed, failed
  results JSONB,

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMP,

  CONSTRAINT fk_assignment_strategy FOREIGN KEY (strategy_id) REFERENCES adaptive_strategies(strategy_id) ON DELETE CASCADE
);

-- Create indexes for task assignments
CREATE INDEX IF NOT EXISTS idx_assignment_strategy ON task_assignments(strategy_id);
CREATE INDEX IF NOT EXISTS idx_assignment_agent ON task_assignments(agent_id);
CREATE INDEX IF NOT EXISTS idx_assignment_status ON task_assignments(status);
CREATE INDEX IF NOT EXISTS idx_assignment_priority ON task_assignments(priority);

-- Strategy pivots tracking (when strategy changes approach)
CREATE TABLE IF NOT EXISTS strategy_pivots (
  pivot_id VARCHAR(36) PRIMARY KEY,
  strategy_id VARCHAR(36) NOT NULL,
  from_approach VARCHAR(50) NOT NULL,
  to_approach VARCHAR(50) NOT NULL,
  reason VARCHAR(500),

  -- What prompted the pivot
  trigger_context JSONB,  -- {low_roi_queries: [], total_queries: number, metrics_at_pivot: {...}}

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_pivot_strategy FOREIGN KEY (strategy_id) REFERENCES adaptive_strategies(strategy_id) ON DELETE CASCADE
);

-- Create indexes for pivot tracking
CREATE INDEX IF NOT EXISTS idx_pivot_strategy ON strategy_pivots(strategy_id);
CREATE INDEX IF NOT EXISTS idx_pivot_created ON strategy_pivots(created_at);

-- Resource allocation optimization history
CREATE TABLE IF NOT EXISTS resource_allocation_history (
  allocation_id VARCHAR(36) PRIMARY KEY,
  strategy_id VARCHAR(36) NOT NULL,
  agent_id VARCHAR(36),
  allocation_timestamp TIMESTAMP NOT NULL,

  -- What was allocated
  web_fetches INT NOT NULL DEFAULT 0,
  llm_calls INT NOT NULL DEFAULT 0,
  time_seconds INT NOT NULL DEFAULT 0,

  -- ROI metrics at time of allocation
  roi_score NUMERIC(5, 3),
  efficiency_score NUMERIC(3, 2),

  -- Allocation outcome
  result_quality NUMERIC(5, 3),
  result_claims INT,

  -- Timestamps
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),

  CONSTRAINT fk_alloc_strategy FOREIGN KEY (strategy_id) REFERENCES adaptive_strategies(strategy_id) ON DELETE CASCADE
);

-- Create indexes for allocation history
CREATE INDEX IF NOT EXISTS idx_alloc_strategy ON resource_allocation_history(strategy_id);
CREATE INDEX IF NOT EXISTS idx_alloc_agent ON resource_allocation_history(agent_id);
CREATE INDEX IF NOT EXISTS idx_alloc_timestamp ON resource_allocation_history(allocation_timestamp);
