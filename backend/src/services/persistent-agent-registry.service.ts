/**
 * Persistent Agent Registry (B6 / GA6)
 * ====================================
 * Gives each specialist role a STABLE agent id that survives process death.
 * Re-spawning the same role reattaches to the same record, so the agent's
 * per-agent memory (agent_memories.agent_id) and calibration/trust
 * (trust_scores.subject_id) accumulate across runs instead of being reset to a
 * fresh uuid each spawn.
 */

import { db } from '../db/client';
import { memoryRetrieval, RetrievedMemory } from './memory-retrieval.service';

export interface PersistentAgent {
  agentId: string;
  role: string;
  memoryNamespace: string;
  reattached: boolean;
}

export interface PersistentAgentContext extends PersistentAgent {
  memories: RetrievedMemory[];
  trustFactor: number | null;
  nResolved: number;
}

export class PersistentAgentRegistryService {
  /**
   * Get-or-create the stable agent for a role WITHOUT side effects on reads.
   * `reattached` is true when the record already existed (a prior run/spawn
   * created it). Use recordSpawn() to count actual spawns.
   */
  async ensureAgent(role: string): Promise<PersistentAgent> {
    const normalized = role.trim().toLowerCase();
    if (!/^[a-z0-9][a-z0-9_-]{1,60}$/.test(normalized)) {
      throw new Error('role must be 2-61 chars of lowercase letters, numbers, _ or -');
    }
    const namespace = `agent:${normalized}`;
    const existing = await db.query<{ agent_id: string; role: string; memory_namespace: string }>(
      `SELECT agent_id, role, memory_namespace FROM persistent_agents WHERE role = $1`,
      [normalized]
    );
    if ((existing.rowCount ?? 0) === 1) {
      const row = existing.rows[0];
      return { agentId: row.agent_id, role: row.role, memoryNamespace: row.memory_namespace, reattached: true };
    }
    const inserted = await db.query<{ agent_id: string; role: string; memory_namespace: string }>(
      `INSERT INTO persistent_agents (role, memory_namespace)
         VALUES ($1, $2)
       ON CONFLICT (role) DO UPDATE SET memory_namespace = EXCLUDED.memory_namespace
       RETURNING agent_id, role, memory_namespace`,
      [normalized, namespace]
    );
    const row = inserted.rows[0];
    // A concurrent create could have won the ON CONFLICT; treat that as new.
    return { agentId: row.agent_id, role: row.role, memoryNamespace: row.memory_namespace, reattached: false };
  }

  /** Record an actual spawn of a role (increments spawn_count). */
  async recordSpawn(role: string): Promise<number> {
    const normalized = role.trim().toLowerCase();
    const result = await db.query<{ spawn_count: number }>(
      `UPDATE persistent_agents SET spawn_count = spawn_count + 1, last_spawned_at = now()
        WHERE role = $1 RETURNING spawn_count`,
      [normalized]
    );
    return result.rows[0]?.spawn_count ?? 0;
  }

  /**
   * Load a role's full persistent context: its stable id, its own memories,
   * and its accumulated trust — the state a re-spawned specialist inherits.
   */
  async loadContext(role: string, goalText: string): Promise<PersistentAgentContext> {
    const agent = await this.ensureAgent(role);
    const memories = await memoryRetrieval.retrieveForPlanning({ goalText, agentId: agent.agentId });
    const trust = await db.query<{ trust_factor: string; n_resolved: number }>(
      `SELECT trust_factor, n_resolved FROM trust_scores
        WHERE subject_id = $1
        ORDER BY window_end DESC, computed_at DESC
        LIMIT 1`,
      [agent.agentId]
    );
    return {
      ...agent,
      memories,
      trustFactor: trust.rowCount ? Number(trust.rows[0].trust_factor) : null,
      nResolved: trust.rowCount ? trust.rows[0].n_resolved : 0,
    };
  }

  /**
   * Write a memory owned by the role's persistent agent (semantic hypothesis).
   */
  async writeAgentMemory(role: string, domain: string, summary: string, content: Record<string, unknown> = {}): Promise<string> {
    const agent = await this.ensureAgent(role);
    const inserted = await db.query<{ id: string }>(
      `INSERT INTO agent_memories (agent_id, memory_type, namespace, domain, summary, content, importance)
       VALUES ($1,'semantic',$2,$3,$4,$5::jsonb,0.5)
       RETURNING id`,
      [agent.agentId, agent.memoryNamespace, domain, summary, JSON.stringify({ ...content, source: 'persistent_agent' })]
    );
    return inserted.rows[0].id;
  }
}

export const persistentAgentRegistry = new PersistentAgentRegistryService();
