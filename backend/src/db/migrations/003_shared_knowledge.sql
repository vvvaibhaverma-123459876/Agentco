-- Shared knowledge base: readable by all agents, writable only by permitted agents
CREATE TABLE IF NOT EXISTS shared_knowledge (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key             VARCHAR(256) NOT NULL UNIQUE,
    content         TEXT NOT NULL,
    content_summary VARCHAR(500),
    tags            TEXT[] DEFAULT '{}',
    source_agent_id VARCHAR(64) NOT NULL REFERENCES agent_state(agent_id),
    pinecone_id     VARCHAR(256),  -- ID of corresponding vector in Pinecone
    confidence_score DECIMAL(4,3) NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    EXECUTE 'CREATE EXTENSION IF NOT EXISTS vector';
    EXECUTE 'ALTER TABLE shared_knowledge ADD COLUMN IF NOT EXISTS embedding vector(384)';
EXCEPTION
    WHEN OTHERS THEN
        ALTER TABLE shared_knowledge ADD COLUMN IF NOT EXISTS embedding TEXT;
END
$$;

-- Only permitted agents may write to shared knowledge (enforced at app layer via tool_registry)
CREATE INDEX IF NOT EXISTS idx_shared_knowledge_tags ON shared_knowledge USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_shared_knowledge_source ON shared_knowledge(source_agent_id);
CREATE INDEX IF NOT EXISTS idx_shared_knowledge_confidence ON shared_knowledge(confidence_score);
