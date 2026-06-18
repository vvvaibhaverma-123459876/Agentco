-- Agent Memories — episodic, semantic, and prediction-lesson memory.
--
-- Separate from agent_memory (key-value tool store): this table holds
-- structured, typed memory entries with immutability enforcement.
--
-- pgvector is NOT available in this environment; embeddings are stored as
-- FLOAT[] and cosine similarity is computed in Python. When pgvector is
-- installed, replace FLOAT[] with vector(1536) and add an ivfflat index.
--
-- IMMUTABILITY: summary and content are write-once after INSERT.
--   To correct a memory, INSERT a new row and set superseded_by on the old one.
--   access_count, last_accessed_at, superseded_by, expires_at may be updated.

CREATE TABLE IF NOT EXISTS agent_memories (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          TEXT NOT NULL,
    memory_type       TEXT NOT NULL CHECK (memory_type IN
                          ('episodic', 'semantic', 'prediction_lesson')),
    namespace         TEXT NOT NULL,
    task_id           TEXT,
    prediction_id     TEXT,
    domain            TEXT,
    summary           TEXT NOT NULL,
    content           JSONB NOT NULL,
    embedding         FLOAT[] DEFAULT NULL,   -- OpenAI text-embedding-3-small (1536-d)
    importance        FLOAT DEFAULT 0.5 CHECK (importance BETWEEN 0 AND 1),
    access_count      INT NOT NULL DEFAULT 0,
    last_accessed_at  TIMESTAMPTZ,
    superseded_by     UUID REFERENCES agent_memories(id),
    expires_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_memories_agent_ns
    ON agent_memories(agent_id, namespace);
CREATE INDEX IF NOT EXISTS idx_memories_domain
    ON agent_memories(domain) WHERE domain IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_type
    ON agent_memories(memory_type);
CREATE INDEX IF NOT EXISTS idx_memories_prediction
    ON agent_memories(prediction_id) WHERE prediction_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_memories_created
    ON agent_memories(created_at DESC);
-- Full-text search on summary (replaces ivfflat since pgvector not available)
CREATE INDEX IF NOT EXISTS idx_memories_summary_fts
    ON agent_memories USING gin(to_tsvector('english', summary));

-- ──────────────────────────────────────────────────────────────────────────────
-- IMMUTABILITY TRIGGER: summary and content are write-once.
-- Permitted mutations: access_count, last_accessed_at, superseded_by, expires_at
-- ──────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_memory_mutation()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.summary IS DISTINCT FROM OLD.summary THEN
        RAISE EXCEPTION
            'MEMORY GUARD: summary is write-once. Insert a new row and set superseded_by to correct. (id=%)',
            OLD.id;
    END IF;
    IF NEW.content IS DISTINCT FROM OLD.content THEN
        RAISE EXCEPTION
            'MEMORY GUARD: content is write-once. Insert a new row and set superseded_by to correct. (id=%)',
            OLD.id;
    END IF;
    -- Block changes to immutable registration fields too
    IF NEW.agent_id IS DISTINCT FROM OLD.agent_id
       OR NEW.memory_type IS DISTINCT FROM OLD.memory_type
       OR NEW.namespace IS DISTINCT FROM OLD.namespace
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
    THEN
        RAISE EXCEPTION
            'MEMORY GUARD: agent_id, memory_type, namespace, created_at are immutable. (id=%)',
            OLD.id;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS memory_immutability ON agent_memories;
CREATE TRIGGER memory_immutability
    BEFORE UPDATE ON agent_memories
    FOR EACH ROW EXECUTE FUNCTION prevent_memory_mutation();

-- ──────────────────────────────────────────────────────────────────────────────
-- DELETE GUARD: memories are append-only.
-- ──────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION prevent_memory_delete()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION
        'MEMORY GUARD: agent_memories is append-only. Memories cannot be deleted. (id=%)',
        OLD.id;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS memory_no_delete ON agent_memories;
CREATE TRIGGER memory_no_delete
    BEFORE DELETE ON agent_memories
    FOR EACH ROW EXECUTE FUNCTION prevent_memory_delete();

COMMENT ON TABLE agent_memories IS
    'Append-only agent memory store. Three types: episodic (what happened), '
    'semantic (what was learned), prediction_lesson (calibration feedback). '
    'summary and content are write-once; corrections use superseded_by linkage. '
    'embedding stored as FLOAT[] (pgvector not available); Python computes cosine sim.';
