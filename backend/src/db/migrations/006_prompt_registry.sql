-- Prompt version registry: version-controlled history of every agent's system prompt
-- Writable only by Config-Agent after human approval is confirmed
CREATE TABLE IF NOT EXISTS prompt_registry (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id        VARCHAR(64) NOT NULL REFERENCES agent_state(agent_id),
    version         VARCHAR(32) NOT NULL,  -- semver: MAJOR.MINOR.PATCH
    version_type    VARCHAR(8) NOT NULL CHECK (version_type IN ('PATCH','MINOR','MAJOR')),
    prompt_content  TEXT NOT NULL,
    prompt_hash     VARCHAR(64) NOT NULL,  -- SHA-256 of prompt_content
    change_summary  TEXT NOT NULL,
    previous_version VARCHAR(32),
    human_approver_id VARCHAR(128) NOT NULL,
    human_approval_token UUID NOT NULL,
    approved_at     TIMESTAMPTZ NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT FALSE,
    rolled_out_pct  DECIMAL(5,2) NOT NULL DEFAULT 0,  -- 0–100%
    rollout_stages  JSONB,  -- stage progress tracking
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_id, version)
);

-- Config-Agent is the only writer — enforced at app layer
CREATE INDEX IF NOT EXISTS idx_prompt_registry_agent ON prompt_registry(agent_id);
CREATE INDEX IF NOT EXISTS idx_prompt_registry_active ON prompt_registry(agent_id, is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_prompt_registry_created ON prompt_registry(created_at DESC);
