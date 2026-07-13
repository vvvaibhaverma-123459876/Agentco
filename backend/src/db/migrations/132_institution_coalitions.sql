-- Migration 132: Institution coalitions (build phase C4).
--
-- Coalitions are temporary, explicit, durable institution-level coordination
-- constructs: negotiation rounds with proposals and counterproposals,
-- accepted commitments, consensus per the coalition's charter rule, retained
-- dissent (never deletable), delegated authority revoked on dissolution, and
-- settlement records preserved for failed coalitions too.
--
-- Distinct from the L8 agent-team `coalition_formations` utility (team
-- composition for work execution) — see docs/civilization/CANONICAL_RUNTIME_MAP.md.

CREATE TABLE IF NOT EXISTS institution_coalitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  name TEXT NOT NULL,
  purpose TEXT NOT NULL DEFAULT '',
  mission_scope TEXT NOT NULL DEFAULT '',
  consensus_rule TEXT NOT NULL DEFAULT 'unanimous'
    CHECK (consensus_rule IN ('unanimous','majority','weighted_majority')),
  charter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  charter_hash TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','negotiating','constituted','active','completing','settled','dissolved','failed')),
  failure_reason TEXT,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  closed_by_actor_id UUID REFERENCES actors(id),
  closed_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (civilization_id, name)
);

CREATE TABLE IF NOT EXISTS coalition_state_transitions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  from_status TEXT NOT NULL,
  to_status TEXT NOT NULL,
  reason TEXT NOT NULL,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS coalition_members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  status TEXT NOT NULL DEFAULT 'invited'
    CHECK (status IN ('invited','negotiating','committed','withdrawn')),
  invited_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coalition_id, institution_id)
);

CREATE TABLE IF NOT EXISTS coalition_threads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  topic TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Messages are attributable and persisted; dissent-type messages also land in
-- coalition_dissents. Append-only.
CREATE TABLE IF NOT EXISTS coalition_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id UUID NOT NULL REFERENCES coalition_threads(id) ON DELETE RESTRICT,
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  from_institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  from_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  message_type TEXT NOT NULL DEFAULT 'message'
    CHECK (message_type IN ('message','proposal','counterproposal','acceptance','rejection','dissent')),
  body TEXT NOT NULL,
  round_number INTEGER,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coalition_messages_coalition
  ON coalition_messages (coalition_id, created_at);

CREATE TABLE IF NOT EXISTS coalition_negotiation_rounds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  round_number INTEGER NOT NULL CHECK (round_number >= 1),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
  opened_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  closed_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coalition_id, round_number)
);

CREATE TABLE IF NOT EXISTS coalition_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  round_number INTEGER NOT NULL,
  proposed_by_institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  proposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  proposal_json JSONB NOT NULL,
  parent_proposal_id UUID REFERENCES coalition_proposals(id),
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','accepted','rejected','superseded')),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coalition_proposals_round
  ON coalition_proposals (coalition_id, round_number);

CREATE TABLE IF NOT EXISTS coalition_commitments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  commitment_json JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'offered'
    CHECK (status IN ('offered','accepted','fulfilled','breached','released')),
  offered_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  accepted_by_actor_id UUID REFERENCES actors(id),
  closed_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_coalition_commitments_coalition
  ON coalition_commitments (coalition_id, status);

CREATE TABLE IF NOT EXISTS coalition_delegations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  from_institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  delegated_authority_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  granted_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_coalition_delegation_active
  ON coalition_delegations (coalition_id, from_institution_id, delegated_authority_key)
  WHERE status = 'active';

-- Consensus results and dissent are append-only history.
CREATE TABLE IF NOT EXISTS coalition_consensus_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  round_number INTEGER NOT NULL,
  consensus_rule TEXT NOT NULL,
  outcome TEXT NOT NULL CHECK (outcome IN ('approved','rejected','deadlocked')),
  tally_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  decided_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coalition_id, round_number)
);

CREATE TABLE IF NOT EXISTS coalition_dissents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  institution_id VARCHAR NOT NULL REFERENCES institutions(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  reason TEXT NOT NULL,
  round_number INTEGER,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS coalition_settlements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  settlement_json JSONB NOT NULL,
  status TEXT NOT NULL DEFAULT 'final' CHECK (status IN ('final')),
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (coalition_id)
);

CREATE TABLE IF NOT EXISTS coalition_escalations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  coalition_id UUID NOT NULL REFERENCES institution_coalitions(id) ON DELETE RESTRICT,
  escalation_type TEXT NOT NULL CHECK (escalation_type IN ('deadlock','commitment_breach')),
  target TEXT NOT NULL CHECK (target IN ('governance','judiciary')),
  reason TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','routed','resolved')),
  routed_at TIMESTAMPTZ,
  resolved_at TIMESTAMPTZ,
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION coalition_status_guard() RETURNS trigger AS $$
BEGIN
  IF OLD.status IN ('settled','dissolved','failed') AND NEW.status IS DISTINCT FROM OLD.status THEN
    RAISE EXCEPTION 'COALITION GUARD: % coalition is terminal', OLD.status;
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.coalition_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'COALITION GUARD: status may only change through the coalition service';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.name IS DISTINCT FROM OLD.name OR NEW.created_by_actor_id IS DISTINCT FROM OLD.created_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'COALITION GUARD: identity columns are immutable';
  END IF;
  -- Charter freezes once the coalition is constituted.
  IF OLD.status NOT IN ('proposed','negotiating')
     AND (NEW.charter_json IS DISTINCT FROM OLD.charter_json
          OR NEW.charter_hash IS DISTINCT FROM OLD.charter_hash
          OR NEW.consensus_rule IS DISTINCT FROM OLD.consensus_rule) THEN
    RAISE EXCEPTION 'COALITION GUARD: charter is frozen after constitution';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_coalition_status_guard ON institution_coalitions;
CREATE TRIGGER trg_coalition_status_guard
  BEFORE UPDATE ON institution_coalitions
  FOR EACH ROW EXECUTE FUNCTION coalition_status_guard();

-- Append-only rows: transitions, messages, consensus results, dissents, settlements.
DROP TRIGGER IF EXISTS trg_coalition_transitions_append_only ON coalition_state_transitions;
CREATE TRIGGER trg_coalition_transitions_append_only
  BEFORE UPDATE ON coalition_state_transitions
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_coalition_messages_append_only ON coalition_messages;
CREATE TRIGGER trg_coalition_messages_append_only
  BEFORE UPDATE ON coalition_messages
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_coalition_consensus_append_only ON coalition_consensus_results;
CREATE TRIGGER trg_coalition_consensus_append_only
  BEFORE UPDATE ON coalition_consensus_results
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_coalition_dissents_append_only ON coalition_dissents;
CREATE TRIGGER trg_coalition_dissents_append_only
  BEFORE UPDATE ON coalition_dissents
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_coalition_settlements_append_only ON coalition_settlements;
CREATE TRIGGER trg_coalition_settlements_append_only
  BEFORE UPDATE ON coalition_settlements
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c4_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C4 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'institution_coalitions','coalition_state_transitions','coalition_members','coalition_threads',
    'coalition_messages','coalition_negotiation_rounds','coalition_proposals','coalition_commitments',
    'coalition_delegations','coalition_consensus_results','coalition_dissents','coalition_settlements',
    'coalition_escalations'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c4_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON coalition_state_transitions, coalition_messages,
  coalition_consensus_results, coalition_dissents, coalition_settlements FROM PUBLIC;
REVOKE DELETE ON institution_coalitions, coalition_members, coalition_threads,
  coalition_negotiation_rounds, coalition_proposals, coalition_commitments,
  coalition_delegations, coalition_escalations FROM PUBLIC;
