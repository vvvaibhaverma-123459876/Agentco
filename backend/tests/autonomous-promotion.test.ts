/**
 * Autonomous Promotion (B3 / GA4)
 * ===============================
 * The autonomy loop's OWN resolved outcomes must trigger the existing
 * promotion pipeline with zero manual promotion calls, gated by the existing
 * thresholds, and audited.
 *
 * Positive: a resolved+scored prediction produced by the run's agent is
 * auto-promoted into a retrievable prediction_lesson memory, with an audit row.
 * Negative: an unresolved prediction promotes nothing and the rejection is
 * audited. Requires the resolution_service DB role (same as the civilization
 * learning e2e slice).
 */

import { describe, expect, test, afterAll } from '@jest/globals';
import { Pool } from 'pg';
import { resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { db } from '../src/db/client';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
import { persistentTrustScorer } from '../src/services/persistent-trust-scorer.service';
import { autonomousPromotion } from '../src/services/autonomous-promotion.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { v4 as uuidv4 } from 'uuid';

function serviceDatabaseUrl(): string {
  return resolutionServiceDatabaseUrl();
}

async function registerPrediction(agentId: string, domain: string, claim: string, resolveIt: boolean): Promise<string> {
  const correlationId = uuidv4();
  const predictionId = await ledgerResolutionService.registerPrediction({
    claim,
    probability: 0.8,
    confidence_basis: { note: 'b3 test' },
    producing_agent_id: agentId,
    producing_prompt_version: 'b3-v1',
    resolution_criterion: 'deterministic ground truth for this test',
    resolution_date: new Date(Date.now() - 60_000),
    ground_truth_source: 'agentco://b3',
    horizon_class: 'short',
    domain,
    claim_type: 'grounded_claim_quality',
    correlation_id: correlationId,
    historical_registration_reason: 'deterministic autonomous-promotion fixture',
  });
  if (resolveIt) {
    const client = await servicePool().connect();
    try {
      const resolution = await ledgerResolutionService.resolveWithClient(client, {
        prediction_id: predictionId,
        resolved_outcome: true,
        correlation_id: correlationId,
      });
      await ledgerResolutionService.recordResolutionEvent(resolution, correlationId);
    } finally {
      client.release();
    }
    await persistentTrustScorer.computeForPrediction(predictionId, correlationId);
  }
  return predictionId;
}

// One shared service pool for the whole suite, closed in afterAll, so we do
// not leak resolution_service connections under the full serial run.
let _servicePool: Pool | null = null;
function servicePool(): Pool {
  if (!_servicePool) _servicePool = new Pool({ connectionString: serviceDatabaseUrl(), max: 2 });
  return _servicePool;
}

describe('autonomous promotion (B3)', () => {
  afterAll(async () => {
    if (_servicePool) await _servicePool.end();
  });

  test('a run\'s resolved outcome auto-promotes a retrievable memory with zero manual calls', async () => {
    const agentId = `autoprom-${uuidv4()}`;
    const runId = `run_${Date.now()}`;
    const domain = `autoprom_${Date.now()}`;
    const marker = `quasar_${Date.now()}`;
    const predictionId = await registerPrediction(agentId, domain, `${marker} claim resolves true`, true);

    // The post-run hook — NO manual promoteResolvedPrediction call anywhere.
    const summary = await autonomousPromotion.promoteResolvedForRun({ runId, agentId });
    expect(summary.promoted).toBe(1);
    expect(summary.rejected).toBe(0);
    const outcome = summary.outcomes.find(o => o.predictionId === predictionId)!;
    expect(outcome.promoted).toBe(true);
    expect(outcome.memoryId).toMatch(/^[0-9a-f-]{36}$/);

    // Audit row records the autonomous promotion.
    const audit = await db.query<{ promoted: boolean; run_id: string; memory_id: string }>(
      `SELECT promoted, run_id, memory_id FROM autonomous_promotions WHERE prediction_id = $1`,
      [predictionId]
    );
    expect(audit.rows[0].promoted).toBe(true);
    expect(audit.rows[0].run_id).toBe(runId);

    // The promoted lesson is retrievable by a later run (chains into the
    // two-run machinery): a prediction_lesson memory exists for this agent.
    const memories = await memoryRetrieval.retrieveForPlanning({
      goalText: `${marker} claim`,
      domain,
      agentId,
    });
    expect(memories.map(m => m.id)).toContain(outcome.memoryId);

    // Idempotent: re-running the hook does not double-promote.
    const again = await autonomousPromotion.promoteResolvedForRun({ runId, agentId });
    expect(again.considered).toBe(0);
  }, 30000);

  test('an unresolved outcome promotes nothing and the rejection is audited', async () => {
    const agentId = `autoprom-neg-${uuidv4()}`;
    const runId = `run_neg_${Date.now()}`;
    const domain = `autoprom_neg_${Date.now()}`;
    const predictionId = await registerPrediction(agentId, domain, 'unresolved claim', false);

    const summary = await autonomousPromotion.promoteResolvedForRun({ runId, agentId });
    expect(summary.promoted).toBe(0);
    expect(summary.rejected).toBe(1);

    const audit = await db.query<{ promoted: boolean; reason: string }>(
      `SELECT promoted, reason FROM autonomous_promotions WHERE prediction_id = $1`,
      [predictionId]
    );
    expect(audit.rows[0].promoted).toBe(false);
    expect(audit.rows[0].reason).toContain('not resolved');

    // No prediction_lesson memory was created for this agent.
    const mem = await db.query(
      `SELECT count(*) n FROM agent_memories WHERE agent_id = $1 AND memory_type = 'prediction_lesson'`,
      [agentId]
    );
    expect(Number((mem.rows[0] as any).n)).toBe(0);
  }, 30000);
});
