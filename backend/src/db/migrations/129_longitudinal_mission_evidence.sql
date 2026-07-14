CREATE TABLE IF NOT EXISTS longitudinal_campaigns (
  campaign_id TEXT PRIMARY KEY,
  campaign_version TEXT NOT NULL,
  benchmark_registry_hash TEXT NOT NULL,
  evidence_tier TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('planned', 'running', 'completed', 'failed', 'superseded')),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS longitudinal_runs (
  run_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL REFERENCES longitudinal_campaigns(campaign_id),
  run_type TEXT NOT NULL,
  commit_sha TEXT NOT NULL,
  branch TEXT NOT NULL,
  dirty_status TEXT NOT NULL CHECK (dirty_status IN ('clean', 'dirty')),
  benchmark_registry_hash TEXT NOT NULL,
  configuration_hash TEXT NOT NULL,
  seed INTEGER NOT NULL,
  provider_classification TEXT NOT NULL CHECK (
    provider_classification IN (
      'deterministic_fixture',
      'simulated',
      'local_model',
      'local_real_service',
      'live_external_provider',
      'hosted_staging',
      'production'
    )
  ),
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed', 'timed_out')),
  manifest_hash TEXT NOT NULL,
  evidence_hash TEXT NOT NULL,
  immutable_after TIMESTAMPTZ,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (campaign_id, seed)
);

CREATE TABLE IF NOT EXISTS longitudinal_run_metrics (
  metric_id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES longitudinal_runs(run_id),
  metric_name TEXT NOT NULL,
  metric_value DOUBLE PRECISION NOT NULL,
  units TEXT NOT NULL,
  evaluator_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (run_id, metric_name, evaluator_version)
);

CREATE TABLE IF NOT EXISTS longitudinal_run_failures (
  failure_id BIGSERIAL PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES longitudinal_runs(run_id),
  benchmark_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  failure_category TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS longitudinal_comparisons (
  comparison_id TEXT PRIMARY KEY,
  baseline_run_id TEXT NOT NULL REFERENCES longitudinal_runs(run_id),
  candidate_run_id TEXT NOT NULL REFERENCES longitudinal_runs(run_id),
  comparison_policy_version TEXT NOT NULL,
  result JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS longitudinal_approvals (
  approval_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL REFERENCES longitudinal_campaigns(campaign_id),
  proposal_id TEXT NOT NULL,
  proposer_identity TEXT NOT NULL,
  approver_identity TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
  rationale TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CHECK (proposer_identity <> approver_identity)
);

CREATE TABLE IF NOT EXISTS longitudinal_promotions (
  promotion_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL REFERENCES longitudinal_campaigns(campaign_id),
  proposal_id TEXT NOT NULL,
  approval_id TEXT REFERENCES longitudinal_approvals(approval_id),
  decision TEXT NOT NULL CHECK (decision IN ('proposal_created', 'rejected', 'blocked')),
  rationale TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS longitudinal_evidence_chain (
  evidence_id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL REFERENCES longitudinal_campaigns(campaign_id),
  run_id TEXT REFERENCES longitudinal_runs(run_id),
  parent_evidence_id TEXT REFERENCES longitudinal_evidence_chain(evidence_id),
  evidence_type TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  previous_hash TEXT,
  chain_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION prevent_longitudinal_completed_run_update()
RETURNS TRIGGER AS $$
BEGIN
  IF OLD.status IN ('completed', 'failed', 'timed_out') THEN
    RAISE EXCEPTION 'completed longitudinal runs are immutable; create a superseding run instead';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS longitudinal_runs_immutable_after_completion ON longitudinal_runs;
CREATE TRIGGER longitudinal_runs_immutable_after_completion
BEFORE UPDATE ON longitudinal_runs
FOR EACH ROW
WHEN (OLD.status IN ('completed', 'failed', 'timed_out'))
EXECUTE FUNCTION prevent_longitudinal_completed_run_update();

CREATE INDEX IF NOT EXISTS idx_longitudinal_runs_campaign ON longitudinal_runs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_longitudinal_metrics_run ON longitudinal_run_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_longitudinal_failures_run ON longitudinal_run_failures(run_id);
CREATE INDEX IF NOT EXISTS idx_longitudinal_chain_campaign ON longitudinal_evidence_chain(campaign_id);
