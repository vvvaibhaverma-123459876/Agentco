-- Persist governance-level coalition formation requests.
-- This table backs GovernanceReputationIntegrationService.formCoalition().
CREATE TABLE IF NOT EXISTS governance_coalition_formations (
  coalition_id VARCHAR(36) PRIMARY KEY,
  initiator_id VARCHAR(36) NOT NULL,
  objective TEXT NOT NULL,
  required_specializations JSONB NOT NULL DEFAULT '[]',
  collaboration_threshold NUMERIC(3, 2) NOT NULL,
  recruited_members JSONB NOT NULL DEFAULT '[]',
  status VARCHAR(50) NOT NULL CHECK (status IN ('forming', 'active', 'dissolved')),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_governance_coalition_initiator
  ON governance_coalition_formations(initiator_id);
CREATE INDEX IF NOT EXISTS idx_governance_coalition_status
  ON governance_coalition_formations(status);
CREATE INDEX IF NOT EXISTS idx_governance_coalition_created
  ON governance_coalition_formations(created_at);
