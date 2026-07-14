-- Migration 134: Civilization economy (build phase C6).
--
-- The treasury layer scopes resource accounts to the civilization hierarchy
-- (civilization/society/institution/coalition/mission/citizen), adds budget
-- proposals and allocations, resource policies (risk/trust-linked), penalties
-- (governance/judiciary authority required), cost attribution, and
-- reconciliation runs. Two-phase reserve/settle stays in the existing
-- ResourceLedgerService (civilization_resource_accounts/…); this layer maps a
-- scope to an actor-owned resource account and governs allocation over it.

CREATE TABLE IF NOT EXISTS treasury_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  scope_type TEXT NOT NULL
    CHECK (scope_type IN ('civilization','society','institution','coalition','mission','citizen')),
  scope_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_account_id UUID NOT NULL REFERENCES civilization_resource_accounts(id),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','frozen','closed')),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (scope_type, scope_id, resource_type)
);
CREATE INDEX IF NOT EXISTS idx_treasury_accounts_scope ON treasury_accounts (scope_type, scope_id);

CREATE TABLE IF NOT EXISTS resource_policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  policy_key TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  max_risk_level TEXT NOT NULL DEFAULT 'critical' CHECK (max_risk_level IN ('low','medium','high','critical')),
  min_trust_factor NUMERIC NOT NULL DEFAULT 0 CHECK (min_trust_factor >= 0 AND min_trust_factor <= 1),
  per_request_cap NUMERIC,
  requires_review_above NUMERIC,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked')),
  created_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  revoked_by_actor_id UUID REFERENCES actors(id),
  revoked_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_resource_policy_active
  ON resource_policies (civilization_id, policy_key) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS budget_proposals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  from_treasury_account_id UUID NOT NULL REFERENCES treasury_accounts(id),
  to_scope_type TEXT NOT NULL,
  to_scope_id TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  amount NUMERIC NOT NULL CHECK (amount > 0),
  justification TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'proposed'
    CHECK (status IN ('proposed','approved','rejected','allocated')),
  proposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  decided_by_actor_id UUID REFERENCES actors(id),
  decided_at TIMESTAMPTZ,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_budget_proposals_status ON budget_proposals (civilization_id, status);

CREATE TABLE IF NOT EXISTS budget_allocations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  budget_proposal_id UUID NOT NULL REFERENCES budget_proposals(id),
  from_treasury_account_id UUID NOT NULL REFERENCES treasury_accounts(id),
  to_treasury_account_id UUID NOT NULL REFERENCES treasury_accounts(id),
  resource_type TEXT NOT NULL,
  amount NUMERIC NOT NULL CHECK (amount > 0),
  debit_transaction_id UUID,
  credit_transaction_id UUID,
  allocated_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (budget_proposal_id)
);

CREATE TABLE IF NOT EXISTS penalties (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  target_scope_type TEXT NOT NULL,
  target_scope_id TEXT NOT NULL,
  treasury_account_id UUID REFERENCES treasury_accounts(id),
  resource_type TEXT NOT NULL,
  amount NUMERIC NOT NULL CHECK (amount > 0),
  reason TEXT NOT NULL,
  authorized_decision_ref TEXT NOT NULL,
  authority TEXT NOT NULL CHECK (authority IN ('governance','judiciary')),
  status TEXT NOT NULL DEFAULT 'imposed' CHECK (status IN ('imposed','applied','reversed')),
  transaction_id UUID,
  imposed_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_penalties_target ON penalties (target_scope_type, target_scope_id);

CREATE TABLE IF NOT EXISTS cost_attribution_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  mission_id UUID REFERENCES missions(id),
  institution_id VARCHAR REFERENCES institutions(id),
  citizen_id UUID REFERENCES citizens(id),
  domain TEXT,
  resource_type TEXT NOT NULL,
  amount NUMERIC NOT NULL CHECK (amount >= 0),
  reason TEXT NOT NULL DEFAULT '',
  recorded_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cost_attribution_mission ON cost_attribution_records (mission_id);
CREATE INDEX IF NOT EXISTS idx_cost_attribution_institution ON cost_attribution_records (institution_id);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  civilization_id UUID NOT NULL REFERENCES civilizations(id) ON DELETE RESTRICT,
  resource_type TEXT NOT NULL,
  computed_balance NUMERIC NOT NULL,
  ledger_balance NUMERIC NOT NULL,
  imbalance NUMERIC NOT NULL,
  balanced BOOLEAN NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  run_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Guards
-- ---------------------------------------------------------------------------

-- Append-only economy history.
DROP TRIGGER IF EXISTS trg_cost_attribution_append_only ON cost_attribution_records;
CREATE TRIGGER trg_cost_attribution_append_only
  BEFORE UPDATE ON cost_attribution_records
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_reconciliation_runs_append_only ON reconciliation_runs;
CREATE TRIGGER trg_reconciliation_runs_append_only
  BEFORE UPDATE ON reconciliation_runs
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();
DROP TRIGGER IF EXISTS trg_budget_allocations_append_only ON budget_allocations;
CREATE TRIGGER trg_budget_allocations_append_only
  BEFORE UPDATE ON budget_allocations
  FOR EACH ROW EXECUTE FUNCTION civilization_kernel_append_only();

-- Penalty imposition fields frozen; only imposed->applied|reversed.
CREATE OR REPLACE FUNCTION penalty_guard() RETURNS trigger AS $$
BEGIN
  IF NEW.civilization_id IS DISTINCT FROM OLD.civilization_id
     OR NEW.target_scope_type IS DISTINCT FROM OLD.target_scope_type
     OR NEW.target_scope_id IS DISTINCT FROM OLD.target_scope_id
     OR NEW.amount IS DISTINCT FROM OLD.amount
     OR NEW.authorized_decision_ref IS DISTINCT FROM OLD.authorized_decision_ref
     OR NEW.authority IS DISTINCT FROM OLD.authority
     OR NEW.imposed_by_actor_id IS DISTINCT FROM OLD.imposed_by_actor_id
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'PENALTY GUARD: penalty imposition fields are immutable';
  END IF;
  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT (OLD.status = 'imposed' AND NEW.status IN ('applied','reversed')) THEN
    RAISE EXCEPTION 'PENALTY GUARD: illegal penalty status transition % -> %', OLD.status, NEW.status;
  END IF;
  NEW.updated_at = now();
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_penalty_guard ON penalties;
CREATE TRIGGER trg_penalty_guard
  BEFORE UPDATE ON penalties
  FOR EACH ROW EXECUTE FUNCTION penalty_guard();

CREATE OR REPLACE FUNCTION c6_no_delete() RETURNS trigger AS $$
BEGIN
  RAISE EXCEPTION 'C6 GUARD: % rows may not be deleted', TG_TABLE_NAME;
END $$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY[
    'treasury_accounts','resource_policies','budget_proposals','budget_allocations',
    'penalties','cost_attribution_records','reconciliation_runs'
  ] LOOP
    EXECUTE format('DROP TRIGGER IF EXISTS trg_%s_no_delete ON %I', t, t);
    EXECUTE format('CREATE TRIGGER trg_%s_no_delete BEFORE DELETE ON %I FOR EACH ROW EXECUTE FUNCTION c6_no_delete()', t, t);
  END LOOP;
END $$;

REVOKE UPDATE, DELETE ON cost_attribution_records, reconciliation_runs, budget_allocations FROM PUBLIC;
REVOKE DELETE ON treasury_accounts, resource_policies, budget_proposals, penalties FROM PUBLIC;
