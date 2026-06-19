-- Agent state table: current status, active tasks, last heartbeat
CREATE TABLE IF NOT EXISTS agent_state (
    agent_id        VARCHAR(64) PRIMARY KEY,
    department      VARCHAR(64) NOT NULL,
    lifecycle_state VARCHAR(32) NOT NULL DEFAULT 'provisioned'
                        CHECK (lifecycle_state IN ('provisioned','staging','canary','production','deprecated','retired')),
    status          VARCHAR(32) NOT NULL DEFAULT 'idle'
                        CHECK (status IN ('idle','active','paused','error')),
    active_task_id  UUID,
    last_heartbeat  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    model           VARCHAR(64) NOT NULL,
    prompt_version  VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_state_dept ON agent_state(department);
CREATE INDEX IF NOT EXISTS idx_agent_state_lifecycle ON agent_state(lifecycle_state);

-- Seed all 29 agents
INSERT INTO agent_state (agent_id, department, lifecycle_state, model, prompt_version) VALUES
  ('ceo-agent',          'executive',           'production', 'claude-opus-4-8',    '1.0.0'),
  ('cfo-agent',          'executive',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('coo-agent',          'executive',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('pm-agent',           'product',             'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('research-agent',     'product',             'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('prioritizer-agent',  'product',             'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('architect-agent',    'engineering',         'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('coder-agent',        'engineering',         'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('reviewer-agent',     'engineering',         'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('devops-agent',       'engineering',         'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('ux-agent',           'design',              'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('brand-agent',        'design',              'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('ab-agent',           'design',              'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('sdr-agent',          'sales',               'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('ae-agent',           'sales',               'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('revops-agent',       'sales',               'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('content-agent',      'marketing',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('seo-agent',          'marketing',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('ads-agent',          'marketing',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('analytics-agent',    'marketing',           'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('support-agent',      'customer_experience', 'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('success-agent',      'customer_experience', 'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('voice-agent',        'customer_experience', 'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('performance-agent',  'people_ops',          'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('recruiter-agent',    'people_ops',          'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('config-agent',       'people_ops',          'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('contract-agent',     'legal',               'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('risk-agent',         'legal',               'production', 'claude-sonnet-4-6',  '1.0.0'),
  ('privacy-agent',      'legal',               'production', 'claude-sonnet-4-6',  '1.0.0')
ON CONFLICT (agent_id) DO NOTHING;
