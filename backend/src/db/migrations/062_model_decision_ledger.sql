-- Phase 1 Brick 2: Model Decision Ledger
-- Audit trail for every model selection decision
-- Enables future calibration-based routing once Phase 0b data is available

CREATE TABLE IF NOT EXISTS model_decision_ledger (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id UUID UNIQUE NOT NULL,
  action_id UUID,
  claim_id UUID,
  model_code VARCHAR(100) NOT NULL,  -- e.g., 'gpt-4o-mini', 'claude-opus-4-8'
  provider VARCHAR(50) NOT NULL,      -- e.g., 'openai', 'anthropic'
  selection_reasoning VARCHAR(255),   -- e.g., 'default', 'fallback', 'cost_optimized'
  request_tokens INT,
  response_tokens INT,
  success BOOLEAN,
  error_message TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  resolved_at TIMESTAMP,

  CONSTRAINT fk_action FOREIGN KEY (action_id) REFERENCES autonomy_actions(id) ON DELETE SET NULL,
  CONSTRAINT fk_claim FOREIGN KEY (claim_id) REFERENCES autonomy_claims(id) ON DELETE SET NULL
);

-- Index for querying by model
CREATE INDEX IF NOT EXISTS idx_model_decision_ledger_model
  ON model_decision_ledger(model_code);

-- Index for queries filtering by success + timestamp (calibration analysis)
CREATE INDEX IF NOT EXISTS idx_model_decision_ledger_success_time
  ON model_decision_ledger(success, created_at DESC) WHERE success IS NOT NULL;

-- Index for correlating to actions/claims
CREATE INDEX IF NOT EXISTS idx_model_decision_ledger_action
  ON model_decision_ledger(action_id) WHERE action_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_model_decision_ledger_claim
  ON model_decision_ledger(claim_id) WHERE claim_id IS NOT NULL;
