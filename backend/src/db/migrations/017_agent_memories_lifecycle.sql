-- Append-only experiential memory lifecycle.
--
-- This intentionally creates agent_memories instead of rewriting the existing
-- agent_memory key/value table used by the backend MemoryStoreService.

CREATE TABLE IF NOT EXISTS agent_memories (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          TEXT NOT NULL,
    memory_type       TEXT NOT NULL CHECK (memory_type IN ('episodic', 'semantic', 'prediction_lesson')),
    namespace         TEXT NOT NULL,
    task_id           TEXT,
    prediction_id     TEXT,
    domain            TEXT,
    summary           TEXT NOT NULL,
    content           JSONB NOT NULL,
    -- Portable embedding storage. pgvector similarity indexes can be added in
    -- a later migration when the Postgres extension is installed.
    embedding         DOUBLE PRECISION[],
    importance        FLOAT DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
    access_count      INT DEFAULT 0,
    last_accessed_at  TIMESTAMPTZ,
    superseded_by     UUID REFERENCES agent_memories(id),
    expires_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memories_agent_ns ON agent_memories(agent_id, namespace);
CREATE INDEX IF NOT EXISTS idx_memories_domain ON agent_memories(domain);
CREATE INDEX IF NOT EXISTS idx_memories_type ON agent_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON agent_memories(created_at DESC);

CREATE OR REPLACE FUNCTION prevent_memory_mutation() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.summary IS DISTINCT FROM NEW.summary OR
       OLD.content IS DISTINCT FROM NEW.content OR
       OLD.agent_id IS DISTINCT FROM NEW.agent_id OR
       OLD.memory_type IS DISTINCT FROM NEW.memory_type OR
       OLD.namespace IS DISTINCT FROM NEW.namespace OR
       OLD.task_id IS DISTINCT FROM NEW.task_id OR
       OLD.prediction_id IS DISTINCT FROM NEW.prediction_id OR
       OLD.domain IS DISTINCT FROM NEW.domain OR
       OLD.embedding IS DISTINCT FROM NEW.embedding OR
       OLD.importance IS DISTINCT FROM NEW.importance OR
       OLD.created_at IS DISTINCT FROM NEW.created_at THEN
        RAISE EXCEPTION 'MEMORY GUARD: memories are append-only. Use superseded_by to link to a corrected memory.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS memory_immutability ON agent_memories;
CREATE TRIGGER memory_immutability
    BEFORE UPDATE ON agent_memories
    FOR EACH ROW EXECUTE FUNCTION prevent_memory_mutation();

CREATE OR REPLACE FUNCTION prevent_memory_delete() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'MEMORY GUARD: memories are append-only and cannot be deleted.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS memory_no_delete ON agent_memories;
CREATE TRIGGER memory_no_delete
    BEFORE DELETE ON agent_memories
    FOR EACH ROW EXECUTE FUNCTION prevent_memory_delete();
