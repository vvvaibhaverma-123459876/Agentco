import { describe, expect, test } from '@jest/globals';
import { v4 as uuidv4 } from 'uuid';
import { db } from '../src/db/client';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

describe('memory retrieval closes the learning loop', () => {
  test('a promoted memory is retrieved for a related goal and lands in the planner prompt', async () => {
    const agentId = `memory-retrieval-${uuidv4()}`;
    const domain = `memret_${uuidv4().slice(0, 8)}`;
    const summary =
      'Prediction about quantum sensor calibration drift resolved incorrect; agent was overconfident at 0.9.';

    const inserted = await db.query<{ id: string }>(
      `INSERT INTO agent_memories
         (agent_id, memory_type, namespace, domain, summary, content, importance)
       VALUES ($1, 'prediction_lesson', 'calibration', $2, $3, $4::jsonb, 0.9)
       RETURNING id`,
      [agentId, domain, summary, JSON.stringify({ brier_score: 0.81, resolved_outcome: false })]
    );
    const memoryId = inserted.rows[0].id;

    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: 'Research quantum sensor calibration drift in field deployments',
      domain,
    });
    expect(memories.map(m => m.id)).toContain(memoryId);
    const retrieved = memories.find(m => m.id === memoryId)!;
    expect(retrieved.summary).toBe(summary);
    expect(retrieved.agentId).toBe(agentId);

    const accessRow = await db.query<{ access_count: number; last_accessed_at: Date | null }>(
      `SELECT access_count, last_accessed_at FROM agent_memories WHERE id = $1`,
      [memoryId]
    );
    expect(accessRow.rows[0].access_count).toBeGreaterThanOrEqual(1);
    expect(accessRow.rows[0].last_accessed_at).not.toBeNull();

    const planner = new AutonomyActionPlannerService();
    const prompt = planner.buildDecisionPrompt({
      goalText: 'Research quantum sensor calibration drift in field deployments',
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: memoryRetrieval.formatForPrompt(memories),
      previousActions: [],
    });
    expect(prompt).toContain(summary);
    expect(prompt).toContain('Learned memories from previously resolved predictions');
  });

  test('superseded and expired memories are not retrieved', async () => {
    const domain = `memret_${uuidv4().slice(0, 8)}`;
    const active = await db.query<{ id: string }>(
      `INSERT INTO agent_memories
         (agent_id, memory_type, namespace, domain, summary, content, importance)
       VALUES ('memret-agent', 'prediction_lesson', 'calibration', $1, 'Corrected lesson about topic X.', '{}'::jsonb, 0.8)
       RETURNING id`,
      [domain]
    );
    const superseded = await db.query<{ id: string }>(
      `INSERT INTO agent_memories
         (agent_id, memory_type, namespace, domain, summary, content, importance)
       VALUES ('memret-agent', 'prediction_lesson', 'calibration', $1, 'Outdated lesson about topic X.', '{}'::jsonb, 0.8)
       RETURNING id`,
      [domain]
    );
    await db.query(`UPDATE agent_memories SET superseded_by = $1 WHERE id = $2`, [
      active.rows[0].id,
      superseded.rows[0].id,
    ]);
    const expired = await db.query<{ id: string }>(
      `INSERT INTO agent_memories
         (agent_id, memory_type, namespace, domain, summary, content, importance, expires_at)
       VALUES ('memret-agent', 'prediction_lesson', 'calibration', $1, 'Expired lesson about topic X.', '{}'::jsonb, 0.8, NOW() - INTERVAL '1 day')
       RETURNING id`,
      [domain]
    );

    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: 'topic X',
      domain,
      limit: 20,
    });
    const ids = memories.map(m => m.id);
    expect(ids).toContain(active.rows[0].id);
    expect(ids).not.toContain(superseded.rows[0].id);
    expect(ids).not.toContain(expired.rows[0].id);
  });
});
