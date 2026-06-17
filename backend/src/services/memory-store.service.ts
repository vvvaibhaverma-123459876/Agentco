/**
 * Memory Store Service — real Postgres reads/writes.
 *
 * Real implementation:
 *   agent memory   → agent_memory table (namespaced, TTL-aware)
 *   shared knowledge → shared_knowledge table + pgvector embedding for semantic search
 *   agent state     → agent_state table
 *
 * Namespace isolation is enforced at both the app layer (this service) and
 * the DB layer (RLS enabled on agent_memory via 002_agent_memory.sql).
 *
 * Semantic embeddings use a lightweight local model (all-MiniLM-L6-v2 via
 * the Python sentence-transformers service on port 5556, falling back to
 * keyword/full-text search if the embedding service is unavailable).
 */
import http from 'http';
import { query } from '../db/client';

const SHARED_KNOWLEDGE_WRITERS = new Set([
  'research-agent', 'voice-agent', 'ceo-agent', 'cfo-agent', 'coo-agent',
]);

export interface MemoryEntry {
  key: string;
  value: unknown;
  ttl_seconds?: number;
}

export interface KnowledgeEntry {
  key: string;
  content: string;
  tags?: string[];
  confidence_score: number;
}

/** Call the local embedding service. Returns null if unavailable. */
async function embed(text: string): Promise<number[] | null> {
  return new Promise((resolve) => {
    const body = JSON.stringify({ text });
    const req = http.request(
      { hostname: '127.0.0.1', port: 5556, path: '/embed', method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } },
      (res) => {
        let data = '';
        res.on('data', (d) => { data += d; });
        res.on('end', () => {
          try { resolve(JSON.parse(data).embedding); }
          catch { resolve(null); }
        });
      }
    );
    req.on('error', () => resolve(null));
    req.setTimeout(2000, () => { req.destroy(); resolve(null); });
    req.write(body);
    req.end();
  });
}

export class MemoryStoreService {
  async readAgentMemory(agentId: string, namespace: string, key: string): Promise<unknown | null> {
    const rows = await query<{ value: unknown }>(
      `SELECT value FROM agent_memory
       WHERE agent_id=$1 AND namespace=$2 AND key=$3
         AND (expires_at IS NULL OR expires_at > NOW())`,
      [agentId, namespace, key]
    );
    return rows.length > 0 ? rows[0].value : null;
  }

  async writeAgentMemory(agentId: string, namespace: string, entry: MemoryEntry): Promise<void> {
    await query(
      `INSERT INTO agent_memory (agent_id, namespace, key, value, ttl_seconds)
       VALUES ($1,$2,$3,$4,$5)
       ON CONFLICT (agent_id, namespace, key)
       DO UPDATE SET value=$4, ttl_seconds=$5, updated_at=NOW()`,
      [agentId, namespace, entry.key, JSON.stringify(entry.value), entry.ttl_seconds ?? null]
    );
  }

  /**
   * Semantic search on shared knowledge using pgvector cosine similarity.
   * Falls back to full-text search (tsvector) if the embedding service is down.
   */
  async readSharedKnowledge(queryText: string, topK = 5): Promise<KnowledgeEntry[]> {
    const embedding = await embed(queryText);

    if (embedding) {
      // Vector similarity search
      const rows = await query<KnowledgeEntry & { id: string }>(
        `SELECT key, content, tags, confidence_score
         FROM shared_knowledge
         ORDER BY embedding <=> $1::vector
         LIMIT $2`,
        [`[${embedding.join(',')}]`, topK]
      );
      return rows;
    }

    // Fallback: full-text search
    const rows = await query<KnowledgeEntry>(
      `SELECT key, content, tags, confidence_score
       FROM shared_knowledge
       WHERE to_tsvector('english', content) @@ plainto_tsquery('english', $1)
       ORDER BY confidence_score DESC
       LIMIT $2`,
      [queryText, topK]
    );
    return rows;
  }

  async writeSharedKnowledge(agentId: string, entry: KnowledgeEntry): Promise<void> {
    if (!SHARED_KNOWLEDGE_WRITERS.has(agentId)) {
      throw new Error(`Agent ${agentId} does not have write access to shared knowledge`);
    }

    const embedding = await embed(entry.content);
    const embeddingParam = embedding ? `[${embedding.join(',')}]` : null;

    await query(
      `INSERT INTO shared_knowledge
         (key, content, tags, source_agent_id, confidence_score, embedding)
       VALUES ($1,$2,$3,$4,$5,$6::vector)
       ON CONFLICT (key) DO UPDATE
         SET content=$2, tags=$3, confidence_score=$5,
             embedding=$6::vector, updated_at=NOW()`,
      [
        entry.key, entry.content,
        entry.tags ?? [],
        agentId, entry.confidence_score,
        embeddingParam,
      ]
    );
  }

  async getAgentState(agentId: string): Promise<Record<string, unknown> | null> {
    const rows = await query<Record<string, unknown>>(
      `SELECT agent_id, department, lifecycle_state, status, active_task_id,
              last_heartbeat, model, prompt_version, created_at, updated_at
       FROM agent_state WHERE agent_id=$1`,
      [agentId]
    );
    return rows.length > 0 ? rows[0] : null;
  }

  async updateHeartbeat(agentId: string): Promise<void> {
    await query(
      `UPDATE agent_state SET last_heartbeat=NOW() WHERE agent_id=$1`,
      [agentId]
    );
  }
}

export const memoryStore = new MemoryStoreService();
