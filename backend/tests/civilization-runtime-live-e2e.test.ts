/**
 * Civilization runtime live E2E (Phase F / G5, G7, G14)
 * =====================================================
 * Proves the civilization LIVES: a runtime event flows through the supervised
 * tick and changes future state, with no LLM/web:
 *
 *   1. seed a claim + lesson memory, then an overdue falsifiable prediction
 *      for that claim (a real runtime event: an unsettled forecast);
 *   2. run one supervised tick — NOT a hand-called service:
 *        - the independent resolver settles the overdue prediction FALSE,
 *        - belief demotion contradicts the claim + demotes the lesson,
 *        - the judiciary rules on the contradiction (G7 wired),
 *        - the persistent civic_reviewer agent operates (G14);
 *   3. the planner's later retrieval no longer serves the demoted lesson and
 *      warns instead — future planning changed;
 *   4. re-spawning the reviewer reattaches to the SAME agent id (persistent
 *      lifecycle across ticks);
 *   5. a kill switch halts the tick within one step.
 */

import crypto from 'crypto';
import { Pool } from 'pg';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { falsifiablePrediction } from '../src/services/falsifiable-prediction.service';
import { independentResolver } from '../src/services/independent-resolver.service';
import { memoryPromotionPipeline } from '../src/services/memory-promotion-pipeline.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { persistentAgentRegistry } from '../src/services/persistent-agent-registry.service';
import { supervisedRuntime } from '../src/services/supervised-runtime.service';
import { killSwitchService } from '../src/services/kill-switch.service';
import { ledgerResolutionService } from '../src/services/resolution-service.service';

const DOMAIN = 'autonomy_research';
const AGENT = `civ-runtime-e2e-${crypto.randomUUID().slice(0, 8)}`;
const MARKER = `cinnabar-ridge-${crypto.randomUUID().slice(0, 6)}`;

let servicePool: Pool;
let goalId: string;
let claimId: string;
let memoryId: string;

async function seedGoal(): Promise<string> {
  const id = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (
       id, title, description, source, domain, expected_value, risk_level,
       autonomy_level_allowed, status, proposed_by
     ) VALUES ($1,$2,$3,'agent_proposed','research',0.7,'low','L3','approved','civ-runtime-e2e')`,
    [id, 'civilization runtime e2e', `civilization runtime ${MARKER}`]
  );
  return id;
}

async function seedEvidence(url: string, snippet: string): Promise<string> {
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goal_actions (
       id, action_id, goal_id, action_type, objective, args, success_criteria,
       risk_level, decided_by, decided_at, reasoning, status
     ) VALUES ($1,$2,$3,'fetch_page','seed','{}','{}','low','civ-runtime-e2e',NOW(),'seed','completed')`,
    [crypto.randomUUID(), actionId, goalId]
  );
  const sourceId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_evidence (
       source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type
     ) VALUES ($1,$2,$3,'seed',$4,NOW(),$5,'web')`,
    [sourceId, actionId, url, snippet, crypto.createHash('sha256').update(snippet).digest('hex')]
  );
  return sourceId;
}

beforeAll(async () => {
  servicePool = new Pool({ connectionString: resolutionServiceDatabaseUrl(), max: 2 });
  goalId = await seedGoal();
});

afterAll(async () => {
  await servicePool.end();
  const active = await killSwitchService.getActive('civilization.supervised_runtime');
  if (active) {
    const actor = await ledgerResolutionService.ensureServiceActor('civ-e2e-operator', ['governance.kill_switch']);
    await killSwitchService.deactivate('civilization.supervised_runtime', actor, 'test cleanup');
  }
});

describe('the civilization lives (Phase F)', () => {
  const claimText = `the ${MARKER} protocol guarantees exactly-once delivery`;

  test('seed: a claim with a promoted lesson and an overdue falsifiable prediction', async () => {
    claimId = crypto.randomUUID();
    const own = await seedEvidence(
      'https://origin.example/spec',
      `${MARKER} protocol guarantees exactly-once delivery per its specification`
    );
    await db.query(
      `INSERT INTO autonomy_claims (claim_id, goal_id, text, status, support_source_ids, support_snippets, generated_at)
       VALUES ($1,$2,$3,'supported',$4::jsonb,$5::jsonb,NOW())`,
      [claimId, goalId, claimText, JSON.stringify([own]), JSON.stringify([claimText])]
    );

    // First prediction resolves TRUE from an independent source, so a lesson
    // gets promoted (this is the belief the runtime will later contradict).
    const p1 = await falsifiablePrediction.registerForClaim({
      claimId,
      claimText,
      supportSourceIds: [own],
      producingAgentId: AGENT,
      domain: DOMAIN,
      runId: 'civ-seed',
      dueInMs: 50,
    });
    await seedEvidence(
      'https://independent.example/review',
      `independent review confirms the ${MARKER} protocol guarantees exactly-once delivery`
    );
    await new Promise(resolve => setTimeout(resolve, 120));
    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: p1.predictionId, serviceClient: client, goalId,
      });
      expect(outcome.status).toBe('resolved_true');
    } finally {
      client.release();
    }
    const promotion = await memoryPromotionPipeline.promoteResolvedPrediction(p1.predictionId);
    expect(promotion.promoted).toBe(true);
    memoryId = promotion.memory_id!;

    // Now an overdue prediction that CANNOT be corroborated (post-registration
    // evidence only) — the runtime will settle it FALSE.
    await falsifiablePrediction.registerForClaim({
      claimId,
      claimText: `${claimText} and stays corroborated indefinitely`,
      supportSourceIds: [own],
      producingAgentId: AGENT,
      domain: DOMAIN,
      runId: 'civ-seed',
      dueInMs: -1000,
      predictionType: 'time_delayed_verification',
    });
  });

  test('one supervised tick settles the prediction FALSE, the judiciary rules, and the reviewer agent operates', async () => {
    const before = await memoryRetrieval.retrieveForPlanning({
      goalText: `research the ${MARKER} protocol delivery guarantees`, domain: DOMAIN, agentId: AGENT,
    });
    expect(before.map(m => m.id)).toContain(memoryId);

    const tick = await supervisedRuntime.tick({ domainKey: DOMAIN });

    expect(tick.halted).toBe(false);
    expect(tick.predictionsResolvedFalse).toBeGreaterThanOrEqual(1);
    expect(tick.contradictionsRuled).toBeGreaterThanOrEqual(1);
    expect(tick.reviewerAgentId).toMatch(/^[0-9a-f-]{36}$/);

    // Judiciary ruling is on the record (G7 wired into runtime).
    const rulings = await db.query(
      `SELECT payload FROM event_log WHERE event_type = 'judiciary.contradiction_ruled'`
    );
    expect(rulings.rows.length).toBeGreaterThanOrEqual(1);

    // Supervised tick event recorded.
    const ticks = await db.query(
      `SELECT payload FROM event_log WHERE event_type = 'supervised_runtime.tick'`
    );
    expect(ticks.rows.length).toBeGreaterThanOrEqual(1);
  });

  test('future planning changed: the demoted lesson is gone and a warning replaces it', async () => {
    const after = await memoryRetrieval.retrieveForPlanning({
      goalText: `research the ${MARKER} protocol delivery guarantees`, domain: DOMAIN, agentId: AGENT,
    });
    expect(after.map(m => m.id)).not.toContain(memoryId);

    const warnings = await memoryRetrieval.demotionWarnings(DOMAIN);
    expect(warnings).toMatch(/CONTRADICTED/);
  });

  test('the persistent reviewer agent reattaches to the same id across ticks (G14 lifecycle)', async () => {
    const first = await persistentAgentRegistry.ensureAgent('civic_reviewer');
    const second = await persistentAgentRegistry.ensureAgent('civic_reviewer');
    expect(first.agentId).toBe(second.agentId);
    expect(second.reattached).toBe(true);
    // It spawned at least once during the tick.
    const row = await db.query<{ spawn_count: number }>(
      `SELECT spawn_count FROM persistent_agents WHERE role = 'civic_reviewer'`
    );
    expect(row.rows[0].spawn_count).toBeGreaterThanOrEqual(1);
  });

  test('a kill switch halts the supervised tick within one step', async () => {
    const actor = await ledgerResolutionService.ensureServiceActor('civ-e2e-operator', ['governance.kill_switch']);
    await killSwitchService.activate('civilization.supervised_runtime', actor, 'e2e kill test');
    try {
      const tick = await supervisedRuntime.tick({ domainKey: DOMAIN });
      expect(tick.halted).toBe(true);
      expect(tick.haltReason).toMatch(/kill switch/);
    } finally {
      await killSwitchService.deactivate('civilization.supervised_runtime', actor, 'e2e cleanup');
    }
  });
});
