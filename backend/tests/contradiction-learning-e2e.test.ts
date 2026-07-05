/**
 * Contradiction learning E2E (Phase D / G3)
 * =========================================
 * Proves the system learns from being wrong, end to end, with no LLM/web:
 *
 *   run 1: claim -> falsifiable prediction -> independent corroboration ->
 *          resolved TRUE -> lesson memory promoted -> retrieval serves it;
 *   later: a second prediction on the SAME claim reaches maturity with no
 *          corroboration -> resolved FALSE -> contradiction recorded, claim
 *          contradicted, promoted memory DEMOTED (append-only);
 *   run 2: retrieval no longer serves the demoted memory, and the planner
 *          context carries an explicit contradiction warning instead —
 *          future behavior differs, history is preserved.
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

const DOMAIN = 'autonomy_research';
const AGENT = `contradiction-e2e-${crypto.randomUUID().slice(0, 8)}`;
// Unique marker so retrieval assertions cannot collide with other suites.
const MARKER = `saffron-gully-${crypto.randomUUID().slice(0, 6)}`;

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
     ) VALUES ($1,$2,$3,'agent_proposed','research',0.7,'low','L3','approved','contradiction-e2e')`,
    [id, 'contradiction learning e2e', `learning-from-wrong test ${MARKER}`]
  );
  return id;
}

async function seedEvidence(url: string, snippet: string): Promise<string> {
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goal_actions (
       id, action_id, goal_id, action_type, objective, args, success_criteria,
       risk_level, decided_by, decided_at, reasoning, status
     ) VALUES ($1,$2,$3,'fetch_page','seed evidence','{}','{}','low','contradiction-e2e',NOW(),'seed','completed')`,
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
});

describe('learning from being wrong (Phase D)', () => {
  const claimText = `the ${MARKER} framework supports streaming replication natively`;

  test('run 1: claim resolves TRUE independently and its lesson is promoted and retrievable', async () => {
    claimId = crypto.randomUUID();
    const own = await seedEvidence(
      'https://origin-docs.example/spec',
      `${MARKER} framework supports streaming replication natively according to its spec`
    );
    await db.query(
      `INSERT INTO autonomy_claims (claim_id, goal_id, text, status, support_source_ids, support_snippets, generated_at)
       VALUES ($1,$2,$3,'supported',$4::jsonb,$5::jsonb,NOW())`,
      [claimId, goalId, claimText, JSON.stringify([own]), JSON.stringify([claimText])]
    );

    const p1 = await falsifiablePrediction.registerForClaim({
      claimId,
      claimText,
      supportSourceIds: [own],
      producingAgentId: AGENT,
      domain: DOMAIN,
      runId: 'contradiction-run-1',
      dueInMs: 50,
    });
    await seedEvidence(
      'https://independent-mirror.example/review',
      `our tests confirm the ${MARKER} framework supports streaming replication natively in production`
    );
    await new Promise(resolve => setTimeout(resolve, 120));

    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: p1.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(outcome.status).toBe('resolved_true');
    } finally {
      client.release();
    }

    const promotion = await memoryPromotionPipeline.promoteResolvedPrediction(p1.predictionId);
    expect(promotion.promoted).toBe(true);
    memoryId = promotion.memory_id!;

    const retrieved = await memoryRetrieval.retrieveForPlanning({
      goalText: `research whether the ${MARKER} framework handles replication`,
      domain: DOMAIN,
      agentId: AGENT,
    });
    expect(retrieved.map(m => m.id)).toContain(memoryId);
  });

  test('a later prediction on the same claim resolves FALSE and demotes the belief', async () => {
    const own = (
      await db.query<{ support_source_ids: string[] }>(
        `SELECT support_source_ids FROM autonomy_claims WHERE claim_id = $1`,
        [claimId]
      )
    ).rows[0].support_source_ids;

    const p2 = await falsifiablePrediction.registerForClaim({
      claimId,
      claimText: `${claimText} and this remains corroborated by fresh sources`,
      supportSourceIds: own,
      producingAgentId: AGENT,
      domain: DOMAIN,
      runId: 'contradiction-run-2',
      dueInMs: -1000, // already mature; no fresh corroboration for THESE tokens
      predictionType: 'time_delayed_verification', // only post-registration evidence counts
    });

    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: p2.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(outcome.status).toBe('resolved_false');
    } finally {
      client.release();
    }

    // Contradiction recorded, claim contradicted, memory demoted — all auditable.
    const contradiction = await db.query(
      `SELECT id, reason FROM contradictions WHERE claim_id = $1`,
      [claimId]
    );
    expect(contradiction.rows.length).toBeGreaterThanOrEqual(1);

    const claim = await db.query<{ status: string }>(
      `SELECT status FROM autonomy_claims WHERE claim_id = $1`,
      [claimId]
    );
    expect(claim.rows[0].status).toBe('contradicted');

    const demotion = await db.query(
      `SELECT reason FROM memory_demotions WHERE memory_id = $1`,
      [memoryId]
    );
    expect(demotion.rows.length).toBe(1);

    // History preserved: the memory row itself still exists, untouched.
    const memory = await db.query(
      `SELECT id FROM agent_memories WHERE id = $1`,
      [memoryId]
    );
    expect(memory.rows.length).toBe(1);
  });

  test('run 2: retrieval excludes the demoted belief and warns the planner instead', async () => {
    const retrieved = await memoryRetrieval.retrieveForPlanning({
      goalText: `research whether the ${MARKER} framework handles replication`,
      domain: DOMAIN,
      agentId: AGENT,
    });
    expect(retrieved.map(m => m.id)).not.toContain(memoryId);

    const warnings = await memoryRetrieval.demotionWarnings(DOMAIN);
    expect(warnings).toMatch(/CONTRADICTED/);
    expect(warnings).toContain(MARKER);

    const events = await db.query(
      `SELECT event_type FROM event_log
        WHERE object_id = $1 AND event_type = 'memory.demoted'`,
      [memoryId]
    );
    expect(events.rows.length).toBeGreaterThanOrEqual(1);
  });
});
