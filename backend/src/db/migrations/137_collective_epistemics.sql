-- Migration 137: Collective epistemics (build phase C9).
--
-- Adds the civilization knowledge provenance graph and retraction machinery on
-- top of the existing L3-L6 evidence/claims/predictions/trust/memory systems.
-- A knowledge node (evidence, claim, prediction, memory, decision) may derive
-- from others via knowledge_provenance_edges. Retracting a node propagates
-- transitively to its dependents: claims are marked retracted, memories are
-- demoted (via the existing memory_demotions), decisions are flagged.

CREATE TABLE IF NOT EXISTS knowledge_provenance_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  from_type TEXT NOT NULL CHECK (from_type IN ('evidence','claim','prediction','memory','decision')),
  from_id TEXT NOT NULL,
  to_type TEXT NOT NULL CHECK (to_type IN ('evidence','claim','prediction','memory','decision')),
  to_id TEXT NOT NULL,
  relation TEXT NOT NULL DEFAULT 'derives_from',
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (from_type, from_id, to_type, to_id, relation),
  CHECK (NOT (from_type = to_type AND from_id = to_id))
);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_from ON knowledge_provenance_edges (from_type, from_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_edges_to ON knowledge_provenance_edges (to_type, to_id);

CREATE TABLE IF NOT EXISTS knowledge_retractions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('evidence','claim','prediction','memory','decision')),
  subject_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  retracted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  propagated_count INTEGER NOT NULL DEFAULT 0,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_knowledge_retractions_subject ON knowledge_retractions (subject_type, subject_id);

CREATE TABLE IF NOT EXISTS retraction_propagations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  retraction_id UUID NOT NULL REFERENCES knowledge_retractions(id) ON DELETE RESTRICT,
  affected_type TEXT NOT NULL,
  affected_id TEXT NOT NULL,
  effect TEXT NOT NULL CHECK (effect IN ('claim_retracted','memory_demoted','decision_flagged','prediction_flagged','evidence_flagged')),
  depth INTEGER NOT NULL DEFAULT 1,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_retraction_propagations_retraction ON retraction_propagations (retraction_id);

-- decision flags: a decision whose supporting knowledge was retracted.
CREATE TABLE IF NOT EXISTS decision_retraction_flags (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  decision_id TEXT NOT NULL,
  retraction_id UUID NOT NULL REFERENCES knowledge_retractions(id) ON DELETE RESTRICT,
  reason TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (decision_id, retraction_id)
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_knowledge_retractions_append_only ON knowledge_retractions;
CREATE OR REPLACE FUNCTION knowledge_retraction_guard() RETURNS trigger AS $$
BEGIN
  -- Only propagated_count may be updated (bookkeeping); all else immutable.
  IF NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.subject_type IS DISTINCT FROM OLD.subject_type
     OR NEW.subject_id IS DISTINCT FROM OLD.subject_id
     OR NEW.reason IS DISTINCT FROM OLD.reason
     OR NEW.retracted_by_actor_id IS DISTINCT FROM OLD.retracted_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'EPISTEMICS GUARD: retraction fields are immutable';
  END IF;
  RETURN NEW;
END $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_knowledge_retractions_append_only
  BEFORE UPDATE ON knowledge_retractions
  FOR EACH ROW EXECUTE FUNCTION knowledge_retraction_guard();

DROP TRIGGER IF EXISTS trg_retraction_propagations_append_only ON retraction_propagations;
CREATE TRIGGER trg_retraction_propagations_append_only
  BEFORE UPDATE ON retraction_propagations FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_knowledge_edges_append_only ON knowledge_provenance_edges;
CREATE TRIGGER trg_knowledge_edges_append_only
  BEFORE UPDATE ON knowledge_provenance_edges FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c9_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C9 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'knowledge_provenance_edges','knowledge_retractions','retraction_propagations','decision_retraction_flags'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c9_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON retraction_propagations, knowledge_provenance_edges, decision_retraction_flags FROM PUBLIC;
REVOKE DELETE ON knowledge_retractions FROM PUBLIC;
