-- Migration 109: L11 conflict judiciary.
--
-- Formalizes contradiction-linked claims into disputes, rulings, and reusable
-- precedents.

CREATE TABLE IF NOT EXISTS disputes (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  dispute_type TEXT NOT NULL CHECK (dispute_type IN ('claim_contradiction', 'policy_conflict', 'resource_dispute', 'trust_appeal')),
  status TEXT NOT NULL DEFAULT 'opened' CHECK (status IN ('open', 'opened', 'under_review', 'evidence_requested', 'evidence_collection', 'hearing', 'mediation', 'ruling_pending', 'ruled', 'appealed', 'final', 'closed')),
  subject_claim_id VARCHAR(36) REFERENCES autonomy_claims(claim_id) ON DELETE RESTRICT,
  counter_claim_id VARCHAR(36) REFERENCES autonomy_claims(claim_id) ON DELETE RESTRICT,
  opened_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  contradiction_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (dispute_type, subject_claim_id, counter_claim_id)
);

ALTER TABLE disputes
  ADD COLUMN IF NOT EXISTS plaintiff_id TEXT,
  ADD COLUMN IF NOT EXISTS defendant_id TEXT,
  ADD COLUMN IF NOT EXISTS critical BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS subject_claim_id VARCHAR(36) REFERENCES autonomy_claims(claim_id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS counter_claim_id VARCHAR(36) REFERENCES autonomy_claims(claim_id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS opened_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS contradiction_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS opened_at TIMESTAMPTZ NOT NULL DEFAULT now();

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'uq_disputes_type_subject_counter'
       AND conrelid = 'disputes'::regclass
  ) THEN
    ALTER TABLE disputes
      ADD CONSTRAINT uq_disputes_type_subject_counter
      UNIQUE (dispute_type, subject_claim_id, counter_claim_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_disputes_status
  ON disputes(status, opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_disputes_subject_claim
  ON disputes(subject_claim_id);
CREATE INDEX IF NOT EXISTS idx_disputes_counter_claim
  ON disputes(counter_claim_id);

CREATE TABLE IF NOT EXISTS rulings (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  dispute_id TEXT NOT NULL REFERENCES disputes(id) ON DELETE RESTRICT,
  outcome TEXT NOT NULL CHECK (outcome IN ('subject_upheld', 'counter_upheld', 'both_rejected', 'insufficient_evidence', 'settled')),
  rationale TEXT NOT NULL,
  precedent_flag BOOLEAN NOT NULL DEFAULT false,
  ruled_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  ruled_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE rulings
  ADD COLUMN IF NOT EXISTS judge_entity_id TEXT,
  ADD COLUMN IF NOT EXISTS ruling TEXT,
  ADD COLUMN IF NOT EXISTS penalty JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS appeal_deadline TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '14 days'),
  ADD COLUMN IF NOT EXISTS outcome TEXT,
  ADD COLUMN IF NOT EXISTS rationale TEXT,
  ADD COLUMN IF NOT EXISTS precedent_flag BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS ruled_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS ruled_at TIMESTAMPTZ NOT NULL DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_rulings_dispute
  ON rulings(dispute_id, ruled_at DESC);
CREATE INDEX IF NOT EXISTS idx_rulings_outcome
  ON rulings(outcome, ruled_at DESC);

CREATE TABLE IF NOT EXISTS precedents (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  ruling_id TEXT NOT NULL UNIQUE REFERENCES rulings(id) ON DELETE RESTRICT,
  dispute_type TEXT NOT NULL,
  outcome TEXT NOT NULL,
  principle TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE precedents
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS outcome TEXT,
  ADD COLUMN IF NOT EXISTS principle TEXT,
  ADD COLUMN IF NOT EXISTS event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_constraint
     WHERE conname = 'uq_precedents_ruling'
       AND conrelid = 'precedents'::regclass
  ) THEN
    ALTER TABLE precedents
      ADD CONSTRAINT uq_precedents_ruling
      UNIQUE (ruling_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_precedents_type_outcome
  ON precedents(dispute_type, outcome, created_at DESC);
