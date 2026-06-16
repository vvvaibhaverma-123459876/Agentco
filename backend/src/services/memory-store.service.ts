/**
 * Memory Store Service — unified API for relational + vector memory.
 * Namespace isolation enforced here and at DB level.
 */

const SHARED_KNOWLEDGE_WRITERS = new Set([
  'research-agent', 'voice-agent', 'ceo-agent', 'cfo-agent', 'coo-agent'
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

export class MemoryStoreService {
  async readAgentMemory(agentId: string, namespace: string, key: string): Promise<unknown | null> {
    // In production: SELECT value FROM agent_memory WHERE agent_id=$1 AND namespace=$2 AND key=$3 AND (expires_at IS NULL OR expires_at > NOW())
    return null;
  }

  async writeAgentMemory(agentId: string, namespace: string, entry: MemoryEntry): Promise<void> {
    // In production: INSERT INTO agent_memory (agent_id, namespace, key, value, ttl_seconds) VALUES ...
    //                ON CONFLICT (agent_id, namespace, key) DO UPDATE SET value=$4, updated_at=NOW()
  }

  async readSharedKnowledge(query: string, topK = 5): Promise<KnowledgeEntry[]> {
    // In production: embed query → pinecone.query(namespace='shared', vector=embedding, topK)
    //                JOIN with shared_knowledge table for metadata
    return [];
  }

  async writeSharedKnowledge(agentId: string, entry: KnowledgeEntry): Promise<void> {
    if (!SHARED_KNOWLEDGE_WRITERS.has(agentId)) {
      throw new Error(`Agent ${agentId} does not have write access to shared knowledge`);
    }
    // In production: embed entry.content → pinecone.upsert → INSERT INTO shared_knowledge
  }

  async getAgentState(agentId: string): Promise<Record<string, unknown> | null> {
    // In production: SELECT * FROM agent_state WHERE agent_id=$1
    return null;
  }

  async updateHeartbeat(agentId: string): Promise<void> {
    // In production: UPDATE agent_state SET last_heartbeat=NOW() WHERE agent_id=$1
  }
}

export const memoryStore = new MemoryStoreService();
