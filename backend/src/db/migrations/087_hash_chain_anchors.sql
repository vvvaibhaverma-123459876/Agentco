-- Migration 087: L3 hash-chain anchors.
--
-- Stores durable snapshots of event_log and decision_log chain heads. This is
-- an internal Postgres anchor, not an external blockchain or L6 commitment.

CREATE TABLE IF NOT EXISTS hash_chain_anchors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  anchor_scope TEXT NOT NULL CHECK (anchor_scope IN ('internal_postgres')),
  event_log_head_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  event_log_head_hash TEXT NOT NULL,
  decision_log_head_id UUID REFERENCES decision_log(log_id) ON DELETE RESTRICT,
  decision_log_head_hash TEXT NOT NULL,
  combined_root_hash TEXT NOT NULL,
  event_count BIGINT NOT NULL CHECK (event_count >= 0),
  decision_count BIGINT NOT NULL CHECK (decision_count >= 0),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hash_chain_anchors_created
  ON hash_chain_anchors(created_at DESC);

REVOKE DELETE ON hash_chain_anchors FROM PUBLIC;
