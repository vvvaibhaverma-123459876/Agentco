-- Migration 088: L4 evidence registry event linkage.
--
-- Adds canonical event provenance for evidence rows created through
-- EvidenceRegistryService. Existing legacy evidence remains readable.

ALTER TABLE autonomy_evidence
  ADD COLUMN IF NOT EXISTS event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS registered_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  ADD COLUMN IF NOT EXISTS metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_evidence_event_log_id ON autonomy_evidence(event_log_id);
CREATE INDEX IF NOT EXISTS idx_evidence_registered_by ON autonomy_evidence(registered_by_actor_id);
