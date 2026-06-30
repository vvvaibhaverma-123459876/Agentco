-- Migration 098: Governance kill switch

CREATE TABLE IF NOT EXISTS governance_kill_switches (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scope TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT true,
  reason TEXT NOT NULL,
  activated_by_actor_id UUID NOT NULL REFERENCES actors(id) ON DELETE RESTRICT,
  deactivated_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  activated_event_log_id UUID NOT NULL REFERENCES event_log(id) ON DELETE RESTRICT,
  deactivated_event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  activated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deactivated_at TIMESTAMPTZ,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_governance_kill_switch_active_scope
  ON governance_kill_switches(scope)
  WHERE active = true;

CREATE INDEX IF NOT EXISTS idx_governance_kill_switch_scope
  ON governance_kill_switches(scope);
