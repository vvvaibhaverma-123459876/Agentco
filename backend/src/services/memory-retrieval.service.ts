/**
 * Memory Retrieval Service
 * ========================
 * Reads promoted memories out of `agent_memories` so that lessons learned
 * from resolved predictions influence future planning decisions.
 *
 * This is the consumer side of the memory promotion pipeline: promotion
 * writes append-only rows; retrieval ranks the active (non-superseded,
 * non-expired) rows against the current goal and returns them for prompt
 * context. Each retrieval bumps access_count/last_accessed_at, which the
 * memory immutability trigger explicitly permits.
 */

import { db } from '../db/client';

export interface RetrievedMemory {
  id: string;
  agentId: string;
  memoryType: string;
  namespace: string;
  domain: string | null;
  summary: string;
  content: Record<string, unknown>;
  importance: number;
  createdAt: Date;
}

export interface MemoryRetrievalQuery {
  goalText: string;
  domain?: string;
  agentId?: string;
  limit?: number;
}

export class MemoryRetrievalService {
  /**
   * Retrieve the most relevant active memories for a planning step.
   * Ranking: domain match, then full-text relevance against the goal text,
   * then importance, then recency.
   */
  async retrieveForPlanning(query: MemoryRetrievalQuery): Promise<RetrievedMemory[]> {
    const limit = Math.max(1, Math.min(query.limit ?? 5, 20));
    const result = await db.query<{
      id: string;
      agent_id: string;
      memory_type: string;
      namespace: string;
      domain: string | null;
      summary: string;
      content: Record<string, unknown>;
      importance: number;
      created_at: Date;
    }>(
      `SELECT id, agent_id, memory_type, namespace, domain, summary, content,
              importance, created_at
         FROM agent_memories
        WHERE superseded_by IS NULL
          AND (expires_at IS NULL OR expires_at > NOW())
          -- Demoted beliefs never steer planning by default (Phase D/G3):
          -- contradicted lessons are excluded, and surfaced separately as
          -- warnings via demotionWarnings().
          AND NOT EXISTS (
                SELECT 1 FROM memory_demotions d WHERE d.memory_id = agent_memories.id
          )
          AND (
                ($2::text IS NOT NULL AND domain = $2)
             OR ($3::text IS NOT NULL AND agent_id = $3)
             OR to_tsvector('english', summary) @@ plainto_tsquery('english', $1)
          )
        ORDER BY
          (CASE WHEN $2::text IS NOT NULL AND domain = $2 THEN 1 ELSE 0 END) DESC,
          ts_rank(to_tsvector('english', summary), plainto_tsquery('english', $1)) DESC,
          importance DESC,
          created_at DESC
        LIMIT $4`,
      [query.goalText, query.domain ?? null, query.agentId ?? null, limit]
    );

    if (result.rows.length > 0) {
      await db.query(
        `UPDATE agent_memories
            SET access_count = access_count + 1,
                last_accessed_at = NOW()
          WHERE id = ANY($1::uuid[])`,
        [result.rows.map(row => row.id)]
      );
    }

    return result.rows.map(row => ({
      id: row.id,
      agentId: row.agent_id,
      memoryType: row.memory_type,
      namespace: row.namespace,
      domain: row.domain,
      summary: row.summary,
      content: row.content,
      importance: Number(row.importance),
      createdAt: row.created_at,
    }));
  }

  /**
   * Recently contradicted beliefs in this domain, formatted as planner
   * warnings: the planner must know a related lesson was WRONG, and why,
   * without the demoted content steering it (Phase D/G3).
   */
  async demotionWarnings(domain: string | null, limit = 3): Promise<string> {
    const rows = await db.query<{ summary: string; reason: string; claim_text: string | null }>(
      `SELECT m.summary, d.reason, ac.text AS claim_text
         FROM memory_demotions d
         JOIN agent_memories m ON m.id = d.memory_id
         LEFT JOIN contradictions c ON c.id = d.contradiction_id
         LEFT JOIN autonomy_claims ac ON ac.claim_id = c.claim_id
        WHERE $1::text IS NULL OR m.domain = $1
        ORDER BY d.created_at DESC
        LIMIT $2`,
      [domain, Math.max(1, Math.min(limit, 10))]
    );
    if (rows.rows.length === 0) return '';
    const lines = rows.rows.map(
      (row, index) =>
        `${index + 1}. CONTRADICTED: "${row.claim_text ?? row.summary}" — ${row.reason}`
    );
    return `Warnings — the following previously-learned beliefs were contradicted by independent evidence and MUST NOT be relied on:\n${lines.join('\n')}`;
  }

  /**
   * Format retrieved memories as a prompt context block for the planner.
   * Returns an empty string when there is nothing to inject.
   */
  formatForPrompt(memories: RetrievedMemory[]): string {
    if (memories.length === 0) return '';
    const lines = memories.map((memory, index) => {
      const domain = memory.domain ? ` [${memory.domain}]` : '';
      return `${index + 1}. (${memory.memoryType}${domain}, importance ${memory.importance.toFixed(2)}) ${memory.summary}`;
    });
    return `Learned memories from previously resolved predictions (use these to avoid repeating past mistakes and to weight your confidence):\n${lines.join('\n')}`;
  }
}

export const memoryRetrieval = new MemoryRetrievalService();
