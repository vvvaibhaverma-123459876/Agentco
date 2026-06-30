import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export interface IndexEvidenceVectorInput {
  source_id: string;
  content_text: string;
  embedding: number[];
  embedding_model: string;
  actor_id?: string | null;
  metadata?: Record<string, unknown>;
  correlation_id?: string;
}

export interface EvidenceVectorDocument {
  id: string;
  evidence_id: string;
  source_id: string;
  content_text: string;
  embedding_model: string;
  embedding_dimensions: number;
  embedding_hash: string;
  indexed_by_actor_id: string | null;
  event_log_id: string | null;
  metadata_json: Record<string, unknown>;
}

export interface VectorSearchInput {
  embedding: number[];
  embedding_model?: string;
  top_k?: number;
}

export interface VectorSearchResult extends EvidenceVectorDocument {
  similarity: number;
  evidence_title: string | null;
  evidence_url: string;
  evidence_source_type: string | null;
}

function requireNonEmpty(value: string | undefined | null, field: string): string {
  const normalized = value?.trim();
  if (!normalized) throw new Error(`${field} is required`);
  return normalized;
}

function isUuid(value?: string | null): boolean {
  return Boolean(value && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value));
}

function validateEmbedding(embedding: number[]): void {
  if (!Array.isArray(embedding) || embedding.length === 0) {
    throw new Error('embedding must contain at least one dimension');
  }
  if (!embedding.every((value) => Number.isFinite(value))) {
    throw new Error('embedding values must be finite numbers');
  }
  const magnitude = Math.sqrt(embedding.reduce((sum, value) => sum + value * value, 0));
  if (magnitude === 0) {
    throw new Error('embedding magnitude must be greater than zero');
  }
}

function embeddingHash(embedding: number[]): string {
  return crypto.createHash('sha256').update(JSON.stringify(embedding)).digest('hex');
}

function dimensions(embedding: number[]): number[] {
  return embedding.map((_, index) => index);
}

export class EvidenceVectorIndexService {
  async indexEvidence(input: IndexEvidenceVectorInput): Promise<EvidenceVectorDocument> {
    this.validateIndexInput(input);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.indexEvidenceWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async indexEvidenceWithClient(client: PoolClient, input: IndexEvidenceVectorInput): Promise<EvidenceVectorDocument> {
    this.validateIndexInput(input);
    const evidence = await client.query<{
      id: string;
      source_id: string;
      registered_by_actor_id: string | null;
    }>(
      `SELECT id, source_id, registered_by_actor_id
         FROM autonomy_evidence
        WHERE source_id = $1
        LIMIT 1`,
      [input.source_id]
    );
    if ((evidence.rowCount ?? 0) !== 1) {
      throw new Error(`registered evidence not found for source_id=${input.source_id}`);
    }

    const actorId = await this.resolveActor(client, input.actor_id ?? evidence.rows[0].registered_by_actor_id);
    const correlationId = input.correlation_id ?? crypto.randomUUID();
    const hash = embeddingHash(input.embedding);

    const canonicalEvent = await eventLog.appendWithClient(client, {
      event_type: 'evidence.vector_indexed',
      actor_id: actorId,
      object_type: 'evidence',
      object_id: evidence.rows[0].id,
      payload: {
        source_id: input.source_id,
        embedding_model: input.embedding_model,
        embedding_dimensions: input.embedding.length,
        embedding_hash: hash,
      },
      correlation_id: correlationId,
    });

    const document = await client.query<EvidenceVectorDocument>(
      `INSERT INTO evidence_vector_documents
         (evidence_id, source_id, content_text, embedding_model, embedding_dimensions,
          embedding_hash, indexed_by_actor_id, event_log_id, metadata_json)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb)
       ON CONFLICT (evidence_id, embedding_model)
       DO UPDATE SET
          source_id = EXCLUDED.source_id,
          content_text = EXCLUDED.content_text,
          embedding_dimensions = EXCLUDED.embedding_dimensions,
          embedding_hash = EXCLUDED.embedding_hash,
          indexed_by_actor_id = EXCLUDED.indexed_by_actor_id,
          event_log_id = EXCLUDED.event_log_id,
          metadata_json = EXCLUDED.metadata_json,
          updated_at = now()
       RETURNING id, evidence_id, source_id, content_text, embedding_model,
                 embedding_dimensions, embedding_hash, indexed_by_actor_id,
                 event_log_id, metadata_json`,
      [
        evidence.rows[0].id,
        input.source_id,
        input.content_text,
        input.embedding_model,
        input.embedding.length,
        hash,
        actorId,
        canonicalEvent.id,
        JSON.stringify(input.metadata ?? {}),
      ]
    );

    await client.query('DELETE FROM evidence_vector_index WHERE document_id = $1', [document.rows[0].id]);
    await client.query(
      `INSERT INTO evidence_vector_index (document_id, dimension, value)
       SELECT $1::uuid, dimension, value
         FROM unnest($2::int[], $3::double precision[]) AS vector(dimension, value)`,
      [document.rows[0].id, dimensions(input.embedding), input.embedding]
    );

    return document.rows[0];
  }

  async search(input: VectorSearchInput): Promise<VectorSearchResult[]> {
    validateEmbedding(input.embedding);
    const topK = Math.max(1, Math.min(input.top_k ?? 5, 50));
    const queryDimensions = dimensions(input.embedding);
    const result = await db.query<VectorSearchResult>(
      `WITH query_vector AS (
          SELECT dimension, value
            FROM unnest($1::int[], $2::double precision[]) AS vector(dimension, value)
        ),
        scored AS (
          SELECT d.id, d.evidence_id, d.source_id, d.content_text, d.embedding_model,
                 d.embedding_dimensions, d.embedding_hash, d.indexed_by_actor_id,
                 d.event_log_id, d.metadata_json,
                 e.title AS evidence_title,
                 e.url AS evidence_url,
                 e.source_type AS evidence_source_type,
                 SUM(i.value * q.value) /
                   NULLIF(SQRT(SUM(i.value * i.value)) * SQRT((SELECT SUM(value * value) FROM query_vector)), 0)
                 AS similarity
            FROM evidence_vector_documents d
            JOIN autonomy_evidence e ON e.id = d.evidence_id
            JOIN evidence_vector_index i ON i.document_id = d.id
            JOIN query_vector q ON q.dimension = i.dimension
           WHERE d.embedding_dimensions = $3
             AND ($4::text IS NULL OR d.embedding_model = $4)
           GROUP BY d.id, e.title, e.url, e.source_type
        )
        SELECT id, evidence_id, source_id, content_text, embedding_model,
               embedding_dimensions, embedding_hash, indexed_by_actor_id,
               event_log_id, metadata_json, evidence_title, evidence_url,
               evidence_source_type, similarity
          FROM scored
         WHERE similarity IS NOT NULL
         ORDER BY similarity DESC, id ASC
         LIMIT $5`,
      [queryDimensions, input.embedding, input.embedding.length, input.embedding_model ?? null, topK]
    );
    return result.rows.map((row) => ({ ...row, similarity: Number(row.similarity) }));
  }

  private validateIndexInput(input: IndexEvidenceVectorInput): void {
    requireNonEmpty(input.source_id, 'source_id');
    requireNonEmpty(input.content_text, 'content_text');
    requireNonEmpty(input.embedding_model, 'embedding_model');
    validateEmbedding(input.embedding);
    if (input.actor_id && !isUuid(input.actor_id)) throw new Error('actor_id must be a UUID when provided');
  }

  private async resolveActor(client: PoolClient, actorId?: string | null): Promise<string> {
    if (actorId && isUuid(actorId)) {
      const existing = await client.query('SELECT 1 FROM actors WHERE id = $1 AND status = $2', [actorId, 'active']);
      if (existing.rowCount === 1) return actorId;
    }

    const name = 'agentco-evidence-vector-index';
    const created = await client.query<{ id: string }>(
      `INSERT INTO actors (actor_type, name, metadata_json)
       VALUES ('service',$1,$2::jsonb)
       ON CONFLICT (actor_type, name) WHERE status = 'active'
       DO UPDATE SET updated_at = actors.updated_at
       RETURNING id`,
      [name, JSON.stringify({ created_by: 'EvidenceVectorIndexService' })]
    );
    await client.query(
      `INSERT INTO service_identities (actor_id, service_name, scopes)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (actor_id) DO NOTHING`,
      [created.rows[0].id, name, JSON.stringify(['evidence.vector_index'])]
    );
    return created.rows[0].id;
  }
}

export const evidenceVectorIndex = new EvidenceVectorIndexService();
