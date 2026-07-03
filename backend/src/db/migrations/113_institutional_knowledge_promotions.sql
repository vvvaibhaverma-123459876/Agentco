-- Migration 113: institutional knowledge promotions.
--
-- Closes the "civilization produces learning" backbone. Institutional claims
-- that survive vetting/synthesis (Production -> Verification -> Adversarial ->
-- Audit) previously dead-ended in autonomy_claims. This table records the
-- promotion of such a surviving claim into durable, append-only
-- agent_memories so the planner's memory-retrieval path can reuse
-- civilization-produced knowledge in later runs.
--
-- One promotion per institutional claim (idempotent). Blocked promotions are
-- recorded too, so an auditor can see WHY a weak/ungrounded institutional
-- claim was not turned into durable knowledge.

CREATE TABLE IF NOT EXISTS institutional_knowledge_promotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  institutional_claim_id TEXT NOT NULL UNIQUE,
  memory_id UUID REFERENCES agent_memories(id) ON DELETE RESTRICT,
  domain TEXT,
  confidence DOUBLE PRECISION,
  finding_type TEXT,
  contributing_institution_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  source_kind TEXT NOT NULL DEFAULT 'synthesis'
    CHECK (source_kind IN ('synthesis', 'vetting')),
  promoted BOOLEAN NOT NULL,
  block_reason TEXT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_institutional_knowledge_promotions_promoted
  ON institutional_knowledge_promotions(promoted, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_institutional_knowledge_promotions_domain
  ON institutional_knowledge_promotions(domain, created_at DESC);
