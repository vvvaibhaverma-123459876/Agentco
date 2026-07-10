/**
 * Self-Memory Loop (B1 / GA1)
 * ===========================
 * The autonomous loop's UPDATE_MEMORY action must produce a memory that the
 * planner's memory-retrieval path can return in a later run. Before B1 this
 * failed: handleUpdateMemory wrote only `autonomy_memory`, which
 * memory-retrieval never reads (it reads `agent_memories`).
 *
 * Provenance requirements proven here:
 *   - the `autonomy_memory` row is still written (reflection/metrics depend on it)
 *   - a retrievable `agent_memories` row is also written, tagged as
 *     self-derived (namespace 'autonomous_self', content.source), at a LOW
 *     importance so it ranks below promoted/verified knowledge and is not
 *     treated as verified.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { ActionSpec, ActionType, ActionStatus, RiskLevel } from '../src/types/action.types';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '015_agent_memories.sql',
    '017_agent_memories_lifecycle.sql',
    '050_autonomy_action_loop.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '114_self_memory_retrievable.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8'));
  }
}

async function makeGoalAndAction(domain: string): Promise<{ goalId: string; actionId: string }> {
  const goalId = crypto.randomUUID();
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (id,title,description,source,domain,expected_value,risk_level,autonomy_level_allowed,status,proposed_by)
     VALUES ($1,'t','t','agent_proposed',$2,0.5,'low','L3','approved','audit')`,
    [goalId, domain]
  );
  await db.query(
    `INSERT INTO autonomy_goal_actions (id,action_id,goal_id,action_type,objective,args,success_criteria,risk_level,decided_by,decided_at,status)
     VALUES ($1,$2,$3,'update_memory','remember','{}','[]','low','audit',NOW(),'planned')`,
    [crypto.randomUUID(), actionId, goalId]
  );
  return { goalId, actionId };
}

describe('self-memory loop (B1)', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('UPDATE_MEMORY output is retrievable by the planner and preserved in autonomy_memory', async () => {
    const executor = new ActionExecutorService();
    const domain = `selfmem_${Date.now()}`;
    const marker = `zetacity_${Date.now()}`;
    const { goalId, actionId } = await makeGoalAndAction(domain);

    const spec: ActionSpec = {
      actionId,
      actionType: ActionType.UPDATE_MEMORY,
      goalId,
      objective: 'Store a learning',
      args: { content: { type: 'learning', text: `The capital of Testland is ${marker}.` } },
      successCriteria: ['stored'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'autonomy_planner',
      decidedAt: new Date(),
    };

    const result = await executor.executeAction(spec);
    expect(result.status).toBe(ActionStatus.COMPLETED);

    // Preserved: autonomy_memory row still written (reflection/metrics depend on it).
    const am = await db.query(`SELECT id FROM autonomy_memory WHERE action_id = $1`, [actionId]);
    expect(am.rowCount).toBe(1);

    // Retrievable: memory-retrieval (the planner's path) returns it.
    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: `What is the capital of Testland ${marker}`,
      domain,
    });
    const self = memories.find(m => m.summary.includes(marker));
    expect(self).toBeDefined();

    // Provenance + trust level: self-derived, low importance, not verified.
    expect(self!.namespace).toBe('autonomous_self');
    expect(self!.memoryType).toBe('episodic');
    expect((self!.content as any).source).toBe('autonomous_update_memory');
    expect(self!.importance).toBeLessThanOrEqual(0.45);
  });

  test('two-run + control: run-1 self-memory reaches the run-2 planner prompt, absent on a cold start', async () => {
    const { AutonomyActionPlannerService } = await import('../src/services/autonomy-action-planner.service');
    const planner = new AutonomyActionPlannerService();
    const executor = new ActionExecutorService();
    const domain = `tworun_${Date.now()}`;
    const marker = `helios_${Date.now()}`;

    // --- Run 1: the loop stores a self-derived learning, then "dies". ---
    const { goalId, actionId } = await makeGoalAndAction(domain);
    await executor.executeAction({
      actionId,
      actionType: ActionType.UPDATE_MEMORY,
      goalId,
      objective: 'Store learning',
      args: { content: { type: 'learning', text: `${marker} panels degrade 0.5% per year in field trials.` } },
      successCriteria: ['stored'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'autonomy_planner',
      decidedAt: new Date(),
    });

    // --- Run 2: a related-but-different task. The planner retrieval path
    // (memoryContext=undefined so it self-populates) must surface run-1 memory. ---
    const run2Prompt = planner.buildDecisionPrompt({
      goalText: `Estimate long-term output of ${marker} panels`,
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: memoryRetrieval.formatForPrompt(
        await memoryRetrieval.retrieveForPlanning({
          goalText: `Estimate long-term output of ${marker} panels`,
          domain,
        })
      ),
      previousActions: [],
    });
    expect(run2Prompt).toContain(marker);
    expect(run2Prompt).toContain('degrade 0.5% per year');

    // --- Control: same run-2 task, fresh domain with no run-1 memory. ---
    const controlPrompt = planner.buildDecisionPrompt({
      goalText: `Estimate long-term output of ${marker} panels`,
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: memoryRetrieval.formatForPrompt(
        await memoryRetrieval.retrieveForPlanning({
          goalText: `Estimate long-term output of ${marker} panels`,
          domain: `control_${Date.now()}`,
        })
      ),
      previousActions: [],
    });
    // Measurable difference attributable to the retrieved memory.
    expect(controlPrompt).not.toContain('degrade 0.5% per year');
    expect(run2Prompt.length).toBeGreaterThan(controlPrompt.length);
  });

  test('self-derived memory ranks below promoted institutional knowledge for the same goal', async () => {
    const executor = new ActionExecutorService();
    const domain = `selfmem_rank_${Date.now()}`;
    const marker = `fusion_${Date.now()}`;
    const { goalId, actionId } = await makeGoalAndAction(domain);

    // A higher-trust promoted memory (importance 0.85) in the same domain.
    await db.query(
      `INSERT INTO agent_memories (agent_id, memory_type, namespace, domain, summary, content, importance)
       VALUES ('civilization:x','semantic','institutional_knowledge',$1,$2,'{"source":"civilization"}'::jsonb,0.85)`,
      [domain, `Institutional consensus about ${marker} reactors.`]
    );

    await executor.executeAction({
      actionId,
      actionType: ActionType.UPDATE_MEMORY,
      goalId,
      objective: 'Store a hunch',
      args: { content: { type: 'learning', text: `A hunch about ${marker} reactors.` } },
      successCriteria: ['stored'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'autonomy_planner',
      decidedAt: new Date(),
    });

    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: `Research ${marker} reactors`,
      domain,
    });
    const selfIdx = memories.findIndex(m => m.namespace === 'autonomous_self');
    const promotedIdx = memories.findIndex(m => m.namespace === 'institutional_knowledge');
    expect(promotedIdx).toBeGreaterThanOrEqual(0);
    expect(selfIdx).toBeGreaterThanOrEqual(0);
    // Promoted knowledge ranks before the self-derived hunch.
    expect(promotedIdx).toBeLessThan(selfIdx);
  });
});
