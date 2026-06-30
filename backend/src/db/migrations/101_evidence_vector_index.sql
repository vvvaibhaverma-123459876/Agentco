-- Migration 101: Canonical evidence vector index.
--
-- Stores embeddings for registered evidence without requiring pgvector. Vectors
-- are normalized into dimension rows so local Postgres can run cosine retrieval
-- and the index remains portable across dev and CI databases.

CREATE TABLE IF NOT EXISTS evidence_vector_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id UUID NOT NULL REFERENCES autonomy_evidence(id) ON DELETE CASCADE,
  source_id VARCHAR(36) NOT NULL REFERENCES autonomy_evidence(source_id) ON DELETE CASCADE,
  content_text TEXT NOT NULL,
  embedding_model TEXT NOT NULL,
  embedding_dimensions INT NOT NULL CHECK (embedding_dimensions > 0),
  embedding_hash TEXT NOT NULL,
  indexed_by_actor_id UUID REFERENCES actors(id) ON DELETE RESTRICT,
  event_log_id UUID REFERENCES event_log(id) ON DELETE RESTRICT,
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (evidence_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_evidence_vector_documents_source
  ON evidence_vector_documents(source_id);
CREATE INDEX IF NOT EXISTS idx_evidence_vector_documents_dimensions
  ON evidence_vector_documents(embedding_model, embedding_dimensions);
CREATE INDEX IF NOT EXISTS idx_evidence_vector_documents_event
  ON evidence_vector_documents(event_log_id);

CREATE TABLE IF NOT EXISTS evidence_vector_index (
  document_id UUID NOT NULL REFERENCES evidence_vector_documents(id) ON DELETE CASCADE,
  dimension INT NOT NULL CHECK (dimension >= 0),
  value DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (document_id, dimension)
);

CREATE INDEX IF NOT EXISTS idx_evidence_vector_index_dimension
  ON evidence_vector_index(dimension);
