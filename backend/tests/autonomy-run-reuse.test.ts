/**
 * Autonomy Run — cross-run lesson reuse (D1 reuse half)
 * =====================================================
 * The forward chain (fetch -> claims -> predictions -> resolution ->
 * promotion) is proven live by the `autonomy` CLI. This test proves the
 * REUSE half deterministically: a lesson promoted by run 1 is retrieved into
 * run 2's planner context, and a cold-start control (no run 1) does not carry
 * it. Uses the real promotion + retrieval + planner paths (no LLM).
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { Pool } from 'pg';
import { describe, expect, test, afterAll } from '@jest/globals';
import { resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { db } from '../src/db/client';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
import { persistentTrustScorer } from '../src/services/persistent-trust-scorer.service';
import { autonomousPromotion } from '../src/services/autonomous-promotion.service';
import { memoryRetrieval } from '../src/services/memory-retrieval.service';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';

let servicePool: Pool | null = null;
function svc(): Pool {
  if (!servicePool) {
    servicePool = new Pool({ connectionString: resolutionServiceDatabaseUrl(), max: 2 });
  }
  return servicePool;
}

describe('autonomy run cross-run reuse (D1)', () => {
  afterAll(async () => { if (servicePool) await servicePool.end(); });

  test('run-1 promoted lesson is retrieved into run-2 planning; cold control lacks it', async () => {
    const agentId = 'autonomy_action_planner';
    const domain = `d1_${Date.now()}`;
    const runId = `run_${Date.now()}`;
    const marker = `helion_${Date.now()}`;

    // --- Run 1: register + resolve a prediction, then auto-promote (no manual promote). ---
    const cid = crypto.randomUUID();
    const predictionId = await ledgerResolutionService.registerPrediction({
      claim: `${marker} coolant loops hold pressure under load`,
      probability: 0.85,
      confidence_basis: {},
      producing_agent_id: agentId,
      producing_prompt_version: 'd1-v1',
      resolution_criterion: 'grounded from evidence',
      resolution_date: new Date(Date.now() - 60_000),
      ground_truth_source: 'agentco://d1',
      horizon_class: 'short',
      domain,
      claim_type: 'grounded_claim_quality',
      correlation_id: cid,
      historical_registration_reason: 'deterministic autonomy-run-reuse fixture',
    });
    const client = await svc().connect();
    try {
      const r = await ledgerResolutionService.resolveWithClient(client, { prediction_id: predictionId, resolved_outcome: true, correlation_id: cid });
      await ledgerResolutionService.recordResolutionEvent(r, cid);
    } finally { client.release(); }
    await persistentTrustScorer.computeForPrediction(predictionId, cid);

    const promo = await autonomousPromotion.promoteResolvedForRun({ runId, agentId });
    expect(promo.promoted).toBeGreaterThanOrEqual(1);
    const memoryId = promo.outcomes.find(o => o.promoted)!.memoryId!;

    // --- Run 2: a related planning step in the same domain/agent retrieves it. ---
    const planner = new AutonomyActionPlannerService();
    const run2Memories = await memoryRetrieval.retrieveForPlanning({ goalText: `${marker} coolant reliability`, domain, agentId });
    expect(run2Memories.map(m => m.id)).toContain(memoryId);
    const run2Prompt = planner.buildDecisionPrompt({
      goalText: `${marker} coolant reliability`, claimsGenerated: 0, evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: memoryRetrieval.formatForPrompt(run2Memories), previousActions: [],
    });
    expect(run2Prompt).toContain('Learned memories');

    // --- Cold control: fresh domain/agent, no run 1. ---
    const coldMemories = await memoryRetrieval.retrieveForPlanning({ goalText: `${marker} coolant reliability`, domain: `cold_${Date.now()}`, agentId: `cold-${crypto.randomUUID().slice(0,8)}` });
    expect(coldMemories.map(m => m.id)).not.toContain(memoryId);
  }, 30000);
});
