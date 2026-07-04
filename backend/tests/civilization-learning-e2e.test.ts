import { describe, expect, test } from '@jest/globals';
import { Pool } from 'pg';
import { resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { db } from '../src/db/client';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
import { persistentTrustScorer } from '../src/services/persistent-trust-scorer.service';
import { memoryPromotionPipeline } from '../src/services/memory-promotion-pipeline.service';
import { ActionSpec, ActionStatus, ActionType, RiskLevel } from '../src/types/action.types';
import { MockWebAdapter } from './support/mock-web-adapter';
import { v4 as uuidv4 } from 'uuid';

function serviceDatabaseUrl(): string {
  return resolutionServiceDatabaseUrl();
}

describe('civilization learning e2e slice', () => {
  test('runs evidence-grounded claim through resolution, trust scoring, and memory promotion', async () => {
    const correlationId = uuidv4();
    const agentId = `civilization-e2e-${uuidv4()}`;
    const executor = new ActionExecutorService();
    executor.setWebAdapter(new MockWebAdapter());

    const fetchSpec: ActionSpec = {
      actionId: uuidv4(),
      actionType: ActionType.FETCH_PAGE,
      goalId: uuidv4(),
      objective: 'Fetch autonomy evidence',
      args: { url: 'https://example.com/autonomy-research' },
      successCriteria: ['Evidence registered'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'test',
      decidedAt: new Date(),
    };
    const fetchResult = await executor.executeAction(fetchSpec);
    expect(fetchResult.status).toBe(ActionStatus.COMPLETED);
    const evidenceSourceId = fetchResult.createdArtifacts[0];

    const claimSpec: ActionSpec = {
      actionId: uuidv4(),
      actionType: ActionType.GENERATE_CLAIM,
      goalId: fetchSpec.goalId,
      objective: 'Generate grounded claim',
      args: {
        claimText: 'Autonomous AI systems show progress in reasoning, planning, and self-correction.',
        supportSourceIds: [evidenceSourceId],
        supportSnippets: ['autonomous AI systems show significant progress in reasoning planning and self correction'],
        confidence: 0.82,
      },
      successCriteria: ['Claim grounded'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'test',
      decidedAt: new Date(),
    };
    const claimResult = await executor.executeAction(claimSpec);
    expect(claimResult.status).toBe(ActionStatus.COMPLETED);
    const claimId = claimResult.observations.claimId;

    const predictionId = await ledgerResolutionService.registerPrediction({
      claim: `Claim ${claimId} will resolve true in this controlled e2e slice`,
      probability: 0.82,
      confidence_basis: { claim_id: claimId, evidence_source_ids: [evidenceSourceId] },
      producing_agent_id: agentId,
      producing_prompt_version: 'civilization-e2e-v1',
      resolution_criterion: 'Synthetic ground truth for this deterministic integration test is true.',
      resolution_date: new Date(Date.now() - 60_000),
      ground_truth_source: 'agentco://e2e/civilization-learning',
      horizon_class: 'short',
      domain: 'civilization_e2e',
      claim_type: 'grounded_claim_quality',
      correlation_id: correlationId,
    });

    const unauthorizedBlocked = await ledgerResolutionService.assertOrdinaryUserCannotResolve(predictionId);
    expect(unauthorizedBlocked).toBe(true);

    const servicePool = new Pool({ connectionString: serviceDatabaseUrl(), max: 1 });
    let resolution;
    try {
      const serviceClient = await servicePool.connect();
      try {
        resolution = await ledgerResolutionService.resolveWithClient(serviceClient, {
          prediction_id: predictionId,
          resolved_outcome: true,
          correlation_id: correlationId,
        });
      } finally {
        serviceClient.release();
      }
    } finally {
      await servicePool.end();
    }
    await ledgerResolutionService.recordResolutionEvent(resolution, correlationId);

    const trust = await persistentTrustScorer.computeForPrediction(predictionId, correlationId);
    expect(Number(trust.trust_factor)).toBeGreaterThan(0);
    expect(trust.subject_id).toBe(agentId);

    const memory = await memoryPromotionPipeline.promoteResolvedPrediction(predictionId, correlationId);
    expect(memory.promoted).toBe(true);
    expect(memory.agent_id).toBe(agentId);

    const eventCounts = await db.query<{ event_type: string; count: string }>(
      `SELECT event_type, COUNT(*)::text AS count
         FROM event_log
        WHERE correlation_id = $1
        GROUP BY event_type`,
      [correlationId]
    );
    const eventTypes = new Set(eventCounts.rows.map(row => row.event_type));
    expect(eventTypes.has('prediction.resolved')).toBe(true);
    expect(eventTypes.has('trust.score.computed')).toBe(true);
    expect(eventTypes.has('memory.promoted')).toBe(true);

    const auditCount = await db.query<{ count: string }>(
      `SELECT COUNT(*)::text AS count FROM decision_log WHERE session_id = $1`,
      [correlationId]
    );
    expect(Number(auditCount.rows[0]?.count ?? 0)).toBeGreaterThanOrEqual(3);
  });
});
