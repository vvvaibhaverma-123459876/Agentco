-- GOVERNANCE-REPUTATION INTEGRATION SYSTEM
-- Voting with reputation-weighted scores, policy approval, coalition coordination

-- Governance votes with reputation weighting
CREATE TABLE IF NOT EXISTS governance_reputation_votes (
  vote_id VARCHAR(36) PRIMARY KEY,
  voter_id VARCHAR(36) NOT NULL,
  proposal_id VARCHAR(36) NOT NULL,
  vote VARCHAR(20) NOT NULL,  -- approve, reject, abstain
  weight NUMERIC(3, 2) NOT NULL,  -- 0-1, based on voter reputation
  voter_reputation NUMERIC(5, 2) NOT NULL,  -- snapshot at vote time
  voter_reliability NUMERIC(3, 2) NOT NULL,
  voter_innovation NUMERIC(3, 2) NOT NULL,
  reasoning TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for vote lookup
CREATE INDEX IF NOT EXISTS idx_governance_votes_proposal ON governance_reputation_votes(proposal_id);
CREATE INDEX IF NOT EXISTS idx_governance_votes_voter ON governance_reputation_votes(voter_id);
CREATE INDEX IF NOT EXISTS idx_governance_votes_created ON governance_reputation_votes(created_at);

-- Governance decisions with weighted aggregate scores
CREATE TABLE IF NOT EXISTS governance_reputation_decisions (
  decision_id VARCHAR(36) PRIMARY KEY,
  proposal_id VARCHAR(36) NOT NULL UNIQUE,
  proposal_type VARCHAR(100) NOT NULL,  -- policy_approval, change_request, coalition_formation
  proposed_by VARCHAR(36) NOT NULL,
  decision VARCHAR(20) NOT NULL,  -- approved, rejected, deferred
  vote_count INT NOT NULL,
  weighted_score NUMERIC(3, 2) NOT NULL,  -- 0-1, normalized approval score
  reasoning TEXT,
  made_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for decision lookup
CREATE INDEX IF NOT EXISTS idx_governance_decisions_proposal ON governance_reputation_decisions(proposal_id);
CREATE INDEX IF NOT EXISTS idx_governance_decisions_type ON governance_reputation_decisions(proposal_type);
CREATE INDEX IF NOT EXISTS idx_governance_decisions_proposer ON governance_reputation_decisions(proposed_by);
CREATE INDEX IF NOT EXISTS idx_governance_decisions_made ON governance_reputation_decisions(made_at);

-- Voting audit trail (who voted, what weight, when)
CREATE TABLE IF NOT EXISTS governance_reputation_audit (
  audit_id VARCHAR(36) PRIMARY KEY,
  voter_id VARCHAR(36) NOT NULL,
  proposal_id VARCHAR(36) NOT NULL,
  action VARCHAR(50) NOT NULL,  -- vote_cast, vote_changed, vote_withdrawn
  previous_vote VARCHAR(20),
  new_vote VARCHAR(20),
  weight_change NUMERIC(3, 2),
  reason TEXT,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for audit
CREATE INDEX IF NOT EXISTS idx_governance_audit_voter ON governance_reputation_audit(voter_id);
CREATE INDEX IF NOT EXISTS idx_governance_audit_proposal ON governance_reputation_audit(proposal_id);
CREATE INDEX IF NOT EXISTS idx_governance_audit_timestamp ON governance_reputation_audit(timestamp);
