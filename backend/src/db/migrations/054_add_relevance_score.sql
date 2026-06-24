-- Phase 1 Task 1: Add relevance_score field to autonomy_claims
-- This stores the goal-keyword overlap score for the source paper
-- Range: 0.0 (no keyword match) to 1.0 (all keywords match)
-- Separate from confidence (OpenAI) to distinguish model confidence from source relevance

ALTER TABLE autonomy_claims ADD COLUMN IF NOT EXISTS relevance_score NUMERIC(3,2) DEFAULT NULL;

-- Index for queries filtering by relevance threshold
CREATE INDEX IF NOT EXISTS idx_autonomy_claims_relevance_score ON autonomy_claims(relevance_score DESC) WHERE relevance_score IS NOT NULL;
