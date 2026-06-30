-- L8 SagaCoordinator: durable multi-step task orchestration with compensation.

CREATE TABLE IF NOT EXISTS saga_executions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  saga_type TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running'
    CHECK (status IN ('running', 'completed', 'failed', 'compensating', 'compensated')),
  actor_id UUID NOT NULL REFERENCES actors(id),
  correlation_id UUID NOT NULL DEFAULT gen_random_uuid(),
  payload JSONB NOT NULL DEFAULT '{}',
  failure_reason TEXT,
  event_log_id UUID REFERENCES event_log(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_saga_executions_status_created
  ON saga_executions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_saga_executions_actor
  ON saga_executions(actor_id);

CREATE TABLE IF NOT EXISTS saga_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  saga_id UUID NOT NULL REFERENCES saga_executions(id) ON DELETE RESTRICT,
  step_name TEXT NOT NULL,
  step_order INTEGER NOT NULL CHECK (step_order >= 0),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'compensation_pending', 'compensated', 'compensation_failed')),
  task_id UUID REFERENCES workflow_tasks(task_id),
  payload JSONB NOT NULL DEFAULT '{}',
  result JSONB,
  error TEXT,
  compensation_payload JSONB,
  event_log_id UUID REFERENCES event_log(id),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (saga_id, step_order),
  UNIQUE (saga_id, step_name)
);

CREATE INDEX IF NOT EXISTS idx_saga_steps_saga_order
  ON saga_steps(saga_id, step_order);
CREATE INDEX IF NOT EXISTS idx_saga_steps_status
  ON saga_steps(status);
