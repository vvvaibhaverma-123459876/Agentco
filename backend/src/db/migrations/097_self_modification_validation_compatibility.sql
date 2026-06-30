-- Migration 097: Self-modification protected-surface validation compatibility

CREATE TABLE IF NOT EXISTS self_modification_validations (
  id UUID PRIMARY KEY,
  candidate_id UUID NOT NULL REFERENCES learner_candidates(id) ON DELETE CASCADE,
  status TEXT NOT NULL CHECK (status IN ('passed', 'blocked')),
  blocked_reasons_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  touched_surfaces_json JSONB NOT NULL DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_self_mod_validations_candidate
  ON self_modification_validations(candidate_id);

CREATE INDEX IF NOT EXISTS idx_self_mod_validations_status
  ON self_modification_validations(status);

CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY,
  event_type TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  status TEXT NOT NULL,
  details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  severity TEXT NOT NULL DEFAULT 'info',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_entity
  ON audit_events(entity_type, entity_id);

CREATE INDEX IF NOT EXISTS idx_audit_events_type
  ON audit_events(event_type);
