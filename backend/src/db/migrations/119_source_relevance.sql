-- 119: goal-relevant source discovery + claim relevance (G4 / Phase B)
-- ====================================================================
-- Source discovery was goal-agnostic: hardcoded seed packs (arxiv/github/
-- stackoverflow front pages) were fetched for ANY goal, and any quotable
-- text became a "grounded" claim regardless of relevance.
--
--   autonomy_source_candidates — every candidate URL considered for a goal,
--     with its derived query, relevance score, accept/reject decision, and
--     discovery method (search / seed_fallback / fixture). Auditable trail of
--     WHY a source was fetched or refused.
--   autonomy_claims.relevance_* — claims now carry a goal-relevance score;
--     low-relevance grounded claims are downgraded, not promoted.

CREATE TABLE IF NOT EXISTS autonomy_source_candidates (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id           UUID,
    query             TEXT NOT NULL,
    url               TEXT NOT NULL,
    title             TEXT,
    relevance_score   NUMERIC NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 1),
    accepted          BOOLEAN NOT NULL,
    reason            TEXT NOT NULL,
    discovery_method  TEXT NOT NULL CHECK (discovery_method IN ('search', 'seed_fallback', 'fixture_search')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_source_candidates_goal ON autonomy_source_candidates(goal_id);

ALTER TABLE autonomy_claims ADD COLUMN IF NOT EXISTS relevance_score NUMERIC;
ALTER TABLE autonomy_claims ADD COLUMN IF NOT EXISTS relevance_reason TEXT;
