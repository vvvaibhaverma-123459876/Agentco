-- Decision-receipt demo flow: a repository review run whose outcome is a
-- cryptographically verifiable receipt. Runs record each pipeline stage
-- (problem -> proposal -> validation -> independent evaluation); the receipt
-- binds all stages into a hash chain signed with the deployment's Ed25519
-- receipt key. Receipts are immutable at the database layer.

CREATE TABLE IF NOT EXISTS repo_review_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_url TEXT NOT NULL,
  source_mode TEXT NOT NULL DEFAULT 'git_clone' CHECK (source_mode IN ('git_clone', 'local_copy')),
  repo_head_sha TEXT,
  status TEXT NOT NULL DEFAULT 'started' CHECK (
    status IN ('started', 'analyzing', 'proposing', 'validating', 'evaluating', 'receipted', 'failed')
  ),
  problem JSONB,
  proposal JSONB,
  validation JSONB,
  evaluation JSONB,
  error TEXT,
  requested_by_actor_id UUID REFERENCES actors(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_repo_review_runs_status ON repo_review_runs(status);
CREATE INDEX IF NOT EXISTS idx_repo_review_runs_created ON repo_review_runs(created_at);

CREATE TABLE IF NOT EXISTS decision_receipts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL UNIQUE REFERENCES repo_review_runs(id) ON DELETE RESTRICT,
  receipt JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  signature TEXT NOT NULL,
  public_key_pem TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION forbid_decision_receipt_mutation() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'DECISION RECEIPT GUARD: receipts are immutable (attempted %)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_decision_receipts_immutable ON decision_receipts;
CREATE TRIGGER trg_decision_receipts_immutable
  BEFORE UPDATE OR DELETE ON decision_receipts
  FOR EACH ROW EXECUTE FUNCTION forbid_decision_receipt_mutation();
