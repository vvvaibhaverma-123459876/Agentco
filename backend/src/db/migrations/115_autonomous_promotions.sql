-- Migration 115: autonomous promotion audit (GA4).
--
-- The autonomy loop's own resolved outcomes must trigger the EXISTING
-- promotion pipelines without a human. This table records every autonomous
-- promotion decision — promoted or rejected — so an auditor can see what was
-- promoted, from which run, triggered by which resolved prediction, and under
-- which threshold. It does not replace any promotion system; it audits the
-- automatic invocation of the existing ones.
--
-- One decision per prediction (idempotent via UNIQUE), so the post-run hook is
-- safe to re-run.

CREATE TABLE IF NOT EXISTS autonomous_promotions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id TEXT NOT NULL,
  prediction_id UUID NOT NULL UNIQUE,
  memory_id UUID,
  promotion_kind TEXT NOT NULL DEFAULT 'prediction_lesson'
    CHECK (promotion_kind IN ('prediction_lesson')),
  promoted BOOLEAN NOT NULL,
  reason TEXT NOT NULL,
  threshold_note TEXT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_autonomous_promotions_run
  ON autonomous_promotions(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_autonomous_promotions_promoted
  ON autonomous_promotions(promoted, created_at DESC);
