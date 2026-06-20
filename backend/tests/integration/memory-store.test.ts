/**
 * Memory Store Integration Tests — real Postgres + pgvector, no mocks.
 *
 * Requires: Postgres on localhost:5432, agent_memory + shared_knowledge tables,
 *           pgvector extension enabled (vector(384) on shared_knowledge).
 *
 * Tests:
 *   1. writeAgentMemory() persists; readAgentMemory() retrieves by agent+namespace+key
 *   2. Agent A's namespace is invisible to Agent B
 *   3. Expired TTL entries are not returned
 *   4. writeSharedKnowledge() persists; readSharedKnowledge() retrieves via full-text
 *   5. Unauthorised agent cannot write to shared knowledge
 *   6. writeSharedKnowledge() is idempotent (upsert)
 */

import crypto from 'crypto';
import { Pool } from 'pg';
import { MemoryStoreService } from '../../src/services/memory-store.service';

const DSN =
  process.env.DATABASE_URL ||
  'postgresql://agentco:password@localhost:5432/agentco';

const db = new Pool({ connectionString: DSN });
const svc = new MemoryStoreService();

const AGENT_A = `test-mem-a-${crypto.randomBytes(3).toString('hex')}`;
const AGENT_B = `test-mem-b-${crypto.randomBytes(3).toString('hex')}`;
const NS = 'test-ns';
const WRITER_AGENT = 'research-agent';

beforeAll(async () => {
  // agent_memory has a FK to agent_state; insert test agent rows
  await db.query(
    `INSERT INTO agent_state (agent_id, department, lifecycle_state, status, model)
     VALUES ($1, 'engineering', 'production', 'idle', 'test-model'),
            ($2, 'engineering', 'production', 'idle', 'test-model')
     ON CONFLICT (agent_id) DO NOTHING`,
    [AGENT_A, AGENT_B]
  );
});

afterAll(async () => {
  // Clean up test data
  await db.query(`DELETE FROM agent_memory WHERE agent_id LIKE 'test-mem-%'`);
  await db.query(`DELETE FROM shared_knowledge WHERE key LIKE 'test-sk-%'`);
  await db.query(`DELETE FROM agent_state WHERE agent_id LIKE 'test-mem-%'`);
  await db.end();
});

describe('Memory Store — real Postgres', () => {
  test('writeAgentMemory() persists and readAgentMemory() retrieves', async () => {
    await svc.writeAgentMemory(AGENT_A, NS, { key: 'foo', value: { data: 42 } });
    const val = await svc.readAgentMemory(AGENT_A, NS, 'foo');
    expect(val).toEqual({ data: 42 });
  });

  test('Agent B cannot read Agent A namespace', async () => {
    await svc.writeAgentMemory(AGENT_A, NS, { key: 'secret', value: 'private' });
    const val = await svc.readAgentMemory(AGENT_B, NS, 'secret');
    // Different agent_id → different row; returns null
    expect(val).toBeNull();
  });

  test('Expired TTL entry is not returned', async () => {
    await svc.writeAgentMemory(AGENT_A, NS, { key: 'ephemeral', value: 'gone', ttl_seconds: 1 });
    // Force expiry: set ttl_seconds to a negative value so the trigger
    // computes expires_at = NOW() + (-1) second = in the past
    await db.query(
      `UPDATE agent_memory SET ttl_seconds = -1
       WHERE agent_id=$1 AND namespace=$2 AND key=$3`,
      [AGENT_A, NS, 'ephemeral']
    );
    const val = await svc.readAgentMemory(AGENT_A, NS, 'ephemeral');
    expect(val).toBeNull();
  });

  test('writeSharedKnowledge() persists; readSharedKnowledge() retrieves via full-text', async () => {
    const key = `test-sk-${crypto.randomBytes(3).toString('hex')}`;
    await svc.writeSharedKnowledge(WRITER_AGENT, {
      key,
      content: 'AgentCo uses blockchain consensus for audit trail verification',
      confidence_score: 0.9,
      tags: ['audit', 'blockchain'],
    });
    const results = await svc.readSharedKnowledge('blockchain audit trail');
    const found = results.find(r => r.key === key);
    expect(found).toBeDefined();
    expect(found!.content).toContain('blockchain');
  });

  test('unauthorised agent cannot write to shared knowledge', async () => {
    await expect(
      svc.writeSharedKnowledge(AGENT_A, {
        key: 'test-sk-denied',
        content: 'should fail',
        confidence_score: 0.5,
      })
    ).rejects.toThrow(/does not have write access/);
  });

  test('writeSharedKnowledge() is idempotent (upsert)', async () => {
    const key = `test-sk-upsert-${crypto.randomBytes(3).toString('hex')}`;
    await svc.writeSharedKnowledge(WRITER_AGENT, { key, content: 'v1', confidence_score: 0.5 });
    await svc.writeSharedKnowledge(WRITER_AGENT, { key, content: 'v2', confidence_score: 0.8 });

    const { rows } = await db.query(
      `SELECT content, confidence_score FROM shared_knowledge WHERE key=$1`, [key]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].content).toBe('v2');
    expect(Number(rows[0].confidence_score)).toBe(0.8);
  });
});
