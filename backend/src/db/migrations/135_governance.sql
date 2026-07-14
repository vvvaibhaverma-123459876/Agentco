-- Migration 135: Governance and constitution (build phase C7).
--
-- Governance proposals move draft -> sponsored -> impact_review -> deliberation
-- -> voting -> approved|rejected -> activation_pending -> active
-- -> superseded|repealed|rolled_back. Approved proposals of type
-- 'policy_change' activate a runtime_policy that the protected-action path
-- actually consults, so activation changes real behaviour and rollback
-- restores it. Tier-0 constitutional invariants cannot be changed by ordinary
-- proposals. Emergency powers integrate the existing kill switch and expire.

CREATE TABLE IF NOT EXISTS governance_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  title TEXT NOT NULL,
  proposal_type TEXT NOT NULL
    CHECK (proposal_type IN ('policy_change','role_grant','institution_power_change',
                             'constitution_change','budget_policy_change','domain_onboarding','general')),
  is_constitutional BOOLEAN NOT NULL DEFAULT false,
  body_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft'
    CHECK (status IN ('draft','sponsored','impact_review','deliberation','voting',
                      'approved','rejected','activation_pending','active',
                      'superseded','repealed','rolled_back')),
  quorum_rule TEXT NOT NULL DEFAULT 'simple_majority'
    CHECK (quorum_rule IN ('simple_majority','supermajority','unanimous')),
  min_votes INTEGER NOT NULL DEFAULT 1 CHECK (min_votes >= 1),
  proposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_governance_proposals_status ON governance_proposals (civilization_id, status);

CREATE TABLE IF NOT EXISTS proposal_sponsors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE RESTRICT,
  sponsor_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proposal_id, sponsor_actor_id)
);

CREATE TABLE IF NOT EXISTS impact_assessments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE RESTRICT,
  assessor_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  risk_level TEXT NOT NULL CHECK (risk_level IN ('low','medium','high','critical')),
  summary TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proposal_id)
);

CREATE TABLE IF NOT EXISTS deliberations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE RESTRICT,
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  position TEXT NOT NULL CHECK (position IN ('support','oppose','neutral')),
  argument TEXT NOT NULL,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE RESTRICT,
  voter_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  vote TEXT NOT NULL CHECK (vote IN ('yes','no','abstain')),
  weight NUMERIC NOT NULL DEFAULT 1 CHECK (weight > 0 AND weight <= 10),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proposal_id, voter_actor_id)
);

CREATE TABLE IF NOT EXISTS governance_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID NOT NULL REFERENCES governance_proposals(id) ON DELETE RESTRICT,
  outcome TEXT NOT NULL CHECK (outcome IN ('approved','rejected')),
  tally_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  decided_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (proposal_id)
);

-- Runtime policies: the enforceable rules consulted by the protected-action
-- path. A policy is activated from an approved proposal and can be rolled back.
CREATE TABLE IF NOT EXISTS runtime_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  proposal_id UUID REFERENCES governance_proposals(id),
  policy_key TEXT NOT NULL,
  effect TEXT NOT NULL CHECK (effect IN ('block','require_review','allow')),
  match_action_type TEXT,
  match_domain TEXT,
  match_min_risk TEXT CHECK (match_min_risk IN ('low','medium','high','critical')),
  description TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','rolled_back','superseded')),
  activated_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  rolled_back_by_actor_id UUID REFERENCES actors(id),
  rolled_back_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_runtime_policies_active
  ON runtime_policies (status, match_action_type) WHERE status = 'active';
CREATE UNIQUE INDEX IF NOT EXISTS uq_runtime_policy_key_active
  ON runtime_policies (civilization_id, policy_key) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS policy_activations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  runtime_policy_id UUID NOT NULL REFERENCES runtime_policies(id) ON DELETE RESTRICT,
  proposal_id UUID REFERENCES governance_proposals(id),
  action TEXT NOT NULL CHECK (action IN ('activated','rolled_back')),
  actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS governance_emergency_powers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  scope TEXT NOT NULL,
  power TEXT NOT NULL,
  reason TEXT NOT NULL,
  authorized_decision_ref TEXT NOT NULL,
  kill_switch_scope TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','expired','revoked')),
  activated_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  expires_at TIMESTAMPTZ NOT NULL,
  ended_at TIMESTAMPTZ,
  ended_by_actor_id UUID REFERENCES actors(id),
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (expires_at > created_at)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_gov_emergency_active
  ON governance_emergency_powers (civilization_id, scope) WHERE status = 'active';

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION governance_proposal_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.proposal_type IS DISTINCT FROM OLD.proposal_type
     OR NEW.proposed_by_actor_id IS DISTINCT FROM OLD.proposed_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'GOVERNANCE GUARD: proposal identity fields are immutable';
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND current_setting('civilization.governance_transition_authorized', true) IS DISTINCT FROM 'true' THEN
    RAISE EXCEPTION 'GOVERNANCE GUARD: proposal status may only change through the governance service';
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_governance_proposal_guard ON governance_proposals;
CREATE TRIGGER trg_governance_proposal_guard
  BEFORE UPDATE ON governance_proposals
  FOR EACH ROW EXECUTE FUNCTION governance_proposal_guard();

DROP TRIGGER IF EXISTS trg_deliberations_append_only ON deliberations;
CREATE TRIGGER trg_deliberations_append_only
  BEFORE UPDATE ON deliberations FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_governance_votes_append_only ON governance_votes;
CREATE TRIGGER trg_governance_votes_append_only
  BEFORE UPDATE ON governance_votes FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_governance_decisions_append_only ON governance_decisions;
CREATE TRIGGER trg_governance_decisions_append_only
  BEFORE UPDATE ON governance_decisions FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_policy_activations_append_only ON policy_activations;
CREATE TRIGGER trg_policy_activations_append_only
  BEFORE UPDATE ON policy_activations FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

CREATE OR REPLACE FUNCTION c7_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C7 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'governance_proposals','proposal_sponsors','impact_assessments','deliberations',
    'governance_votes','governance_decisions','runtime_policies','policy_activations',
    'governance_emergency_powers'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c7_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON deliberations, governance_votes, governance_decisions, policy_activations FROM PUBLIC;
REVOKE DELETE ON governance_proposals, proposal_sponsors, impact_assessments,
  runtime_policies, governance_emergency_powers FROM PUBLIC;
