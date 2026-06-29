-- Migration 076: Build ledger runtime mirror
--
-- Mirrors BUILD_LEDGER.yaml for runtime introspection and /system build-status
-- surfaces. The YAML remains the authoritative source; this table stores the
-- latest synchronized view.

CREATE TABLE IF NOT EXISTS build_ledger (
  item_id TEXT PRIMARY KEY,
  layer TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('not_started', 'in_progress', 'done', 'verified', 'blocked')),
  depends_on JSONB NOT NULL DEFAULT '[]'::jsonb,
  artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
  tests JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes TEXT,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_build_ledger_layer ON build_ledger(layer);
CREATE INDEX IF NOT EXISTS idx_build_ledger_status ON build_ledger(status);
