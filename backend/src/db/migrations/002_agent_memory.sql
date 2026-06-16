-- Agent-specific persistent memory with TTL and namespace isolation
CREATE TABLE IF NOT EXISTS agent_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    VARCHAR(64) NOT NULL REFERENCES agent_state(agent_id),
    namespace   VARCHAR(128) NOT NULL,
    key         VARCHAR(256) NOT NULL,
    value       JSONB NOT NULL,
    ttl_seconds INTEGER,
    expires_at  TIMESTAMPTZ GENERATED ALWAYS AS (
                    CASE WHEN ttl_seconds IS NOT NULL
                    THEN created_at + (ttl_seconds * INTERVAL '1 second')
                    ELSE NULL END
                ) STORED,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_id, namespace, key)
);

-- Namespace isolation enforced at DB level
ALTER TABLE agent_memory ENABLE ROW LEVEL SECURITY;

CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX idx_agent_memory_ns_key ON agent_memory(namespace, key);
CREATE INDEX idx_agent_memory_expires ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;

-- Auto-cleanup expired entries
CREATE OR REPLACE FUNCTION cleanup_expired_memory() RETURNS void AS $$
    DELETE FROM agent_memory WHERE expires_at < NOW();
$$ LANGUAGE SQL;
