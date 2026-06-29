-- Migration 085: allow authority decisions for missing actors to be recorded.
--
-- 084 originally required authority_decision_chains.actor_id to reference an
-- existing actor. Missing-actor denials are security-significant too, so record
-- the requested actor id as text and keep actor_id nullable when no FK exists.

ALTER TABLE authority_decision_chains
  ALTER COLUMN actor_id DROP NOT NULL;

ALTER TABLE authority_decision_chains
  ADD COLUMN IF NOT EXISTS requested_actor_id TEXT NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS idx_authority_decision_chains_requested_actor
  ON authority_decision_chains(requested_actor_id, created_at DESC);
