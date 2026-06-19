-- Agent-specific persistent memory with TTL and namespace isolation
CREATE TABLE IF NOT EXISTS agent_memory (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    VARCHAR(64) NOT NULL REFERENCES agent_state(agent_id),
    namespace   VARCHAR(128) NOT NULL,
    key         VARCHAR(256) NOT NULL,
    value       JSONB NOT NULL,
    ttl_seconds INTEGER,
    -- expires_at is derived from created_at + ttl_seconds, but
    -- (timestamptz + interval) is STABLE, not IMMUTABLE, so it cannot be a
    -- GENERATED column on PostgreSQL. It is maintained by the trigger below.
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (agent_id, namespace, key)
);

-- Keep expires_at consistent with created_at + ttl_seconds on every write.
CREATE OR REPLACE FUNCTION set_agent_memory_expires_at() RETURNS trigger AS $$
BEGIN
    IF NEW.ttl_seconds IS NOT NULL THEN
        NEW.expires_at := NEW.created_at + (NEW.ttl_seconds * INTERVAL '1 second');
    ELSE
        NEW.expires_at := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_agent_memory_expires_at ON agent_memory;
CREATE TRIGGER trg_agent_memory_expires_at
    BEFORE INSERT OR UPDATE ON agent_memory
    FOR EACH ROW EXECUTE FUNCTION set_agent_memory_expires_at();

-- Namespace isolation enforced at DB level
ALTER TABLE agent_memory ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent ON agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_ns_key ON agent_memory(namespace, key);
CREATE INDEX IF NOT EXISTS idx_agent_memory_expires ON agent_memory(expires_at) WHERE expires_at IS NOT NULL;

-- Auto-cleanup expired entries
CREATE OR REPLACE FUNCTION cleanup_expired_memory() RETURNS void AS $$
    DELETE FROM agent_memory WHERE expires_at < NOW();
$$ LANGUAGE SQL;
