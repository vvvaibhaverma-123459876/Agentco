/**
 * Grounded Resolver (B4 / GA3)
 * ============================
 * Predictions resolve against REAL fetched evidence, only when the resolution
 * justification is grounded, through the existing resolution_service firewall;
 * the resulting trust re-ranks agents. Ungrounded justifications leave the
 * prediction OPEN. Ordinary DB users still cannot resolve (firewall regression).
 */

import crypto from 'crypto';
import fs from 'fs';
import http from 'http';
import path from 'path';
import { Pool } from 'pg';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
import { groundedResolver } from '../src/services/grounded-resolver.service';
import { calibrationAwareRouting } from '../src/services/calibration-aware-routing.service';
import { ActionType, RiskLevel } from '../src/types/action.types';

const PORT = 18955;

function serviceDatabaseUrl(): string {
  const base = new URL(process.env.AGENTCO_TEST_DATABASE_URL ?? process.env.DATABASE_URL ?? 'postgresql://agentco:password@localhost:5432/agentco');
  base.username = 'resolution_service';
  base.password = process.env.RESOLUTION_SERVICE_PASSWORD ?? 'resolution-service-dev-password';
  return base.toString();
}

let servicePool: Pool;

async function fetchEvidence(executor: ActionExecutorService, url: string): Promise<string> {
  const goalId = crypto.randomUUID();
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (id,title,description,source,domain,expected_value,risk_level,autonomy_level_allowed,status,proposed_by)
     VALUES ($1,'t','t','agent_proposed','resolve',0.5,'low','L3','approved','audit')`,
    [goalId]
  );
  await db.query(
    `INSERT INTO autonomy_goal_actions (id,action_id,goal_id,action_type,objective,args,success_criteria,risk_level,decided_by,decided_at,status)
     VALUES ($1,$2,$3,'fetch_page','x','{}','[]','low','audit',NOW(),'planned')`,
    [crypto.randomUUID(), actionId, goalId]
  );
  const result = await executor.executeAction({
    actionId, actionType: ActionType.FETCH_PAGE, goalId, objective: 'fetch',
    args: { url }, successCriteria: ['f'], riskLevel: RiskLevel.LOW, decidedBy: 'audit', decidedAt: new Date(),
  });
  return result.createdArtifacts[0];
}

async function registerPrediction(agentId: string, domain: string, probability: number): Promise<string> {
  return ledgerResolutionService.registerPrediction({
    claim: 'grid frequency will stay within tolerance',
    probability,
    confidence_basis: {},
    producing_agent_id: agentId,
    producing_prompt_version: 'b4-v1',
    resolution_criterion: 'resolved from fetched evidence',
    resolution_date: new Date(Date.now() - 60_000),
    ground_truth_source: 'agentco://b4',
    horizon_class: 'short',
    domain,
    claim_type: 'grounded_claim_quality',
    correlation_id: crypto.randomUUID(),
  });
}

describe('grounded resolver (B4)', () => {
  let server: http.Server;
  const saved: Record<string, string | undefined> = {};

  beforeAll(async () => {
    for (const name of ['004_decision_log.sql', '009_trust_scores.sql', '011_prediction_ledger.sql', '050_autonomy_action_loop.sql', '079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql']) {
      await db.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8'));
    }
    server = http.createServer((_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<html><body><p>Grid frequency remained within tolerance across the full reporting period.</p></body></html>');
    });
    await new Promise<void>(r => server.listen(PORT, r));
    saved.AGENTCO_ALLOW_LOOPBACK_FETCH = process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = '1';
    servicePool = new Pool({ connectionString: serviceDatabaseUrl(), max: 2 });
  });

  afterAll(async () => {
    await new Promise<void>((r, j) => server.close(e => (e ? j(e) : r())));
    await servicePool.end();
    if (saved.AGENTCO_ALLOW_LOOPBACK_FETCH === undefined) delete process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    else process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = saved.AGENTCO_ALLOW_LOOPBACK_FETCH;
  });

  test('resolves predictions from fetched evidence and the real outcome re-ranks agents; ungrounded justification stays open', async () => {
    const executor = new ActionExecutorService();
    const domain = `b4_${Date.now()}`;
    const sourceId = await fetchEvidence(executor, `http://127.0.0.1:${PORT}/report`);

    // A well-calibrated agent: confident (0.9) and correct.
    const goodAgent = `good-${crypto.randomUUID().slice(0, 8)}`;
    // A poorly-calibrated agent: confident (0.9) but WRONG.
    const poorAgent = `poor-${crypto.randomUUID().slice(0, 8)}`;

    const goodIds = [await registerPrediction(goodAgent, domain, 0.9), await registerPrediction(goodAgent, domain, 0.85)];
    const poorIds = [await registerPrediction(poorAgent, domain, 0.9), await registerPrediction(poorAgent, domain, 0.92)];

    const client = await servicePool.connect();
    let resolvedCount = 0;
    try {
      // Grounded justification: a real subsequence of the fetched page.
      const groundedJustification = 'grid frequency remained within tolerance';
      for (const id of goodIds) {
        const r = await groundedResolver.resolveFromEvidence({ predictionId: id, evidenceSourceIds: [sourceId], resolvedOutcome: true, justification: groundedJustification, serviceClient: client });
        if (r.resolved) resolvedCount++;
      }
      // Poor agent was confidently wrong: same evidence resolves the outcome
      // true, but their high-probability predictions are incorrect.
      for (const id of poorIds) {
        const r = await groundedResolver.resolveFromEvidence({ predictionId: id, evidenceSourceIds: [sourceId], resolvedOutcome: false, justification: groundedJustification, serviceClient: client });
        if (r.resolved) resolvedCount++;
      }

      // Ungrounded justification (not in the page) must NOT resolve.
      const openId = await registerPrediction(goodAgent, domain, 0.8);
      const ungrounded = await groundedResolver.resolveFromEvidence({ predictionId: openId, evidenceSourceIds: [sourceId], resolvedOutcome: true, justification: 'the reactor achieved fusion ignition', serviceClient: client });
      expect(ungrounded.resolved).toBe(false);
      expect(ungrounded.reason).toContain('not grounded');
      const stillOpen = await db.query(`SELECT resolved FROM prediction_ledger WHERE prediction_id = $1`, [openId]);
      expect(stillOpen.rows[0].resolved).toBe(false);
    } finally {
      client.release();
    }

    expect(resolvedCount).toBeGreaterThanOrEqual(2);

    // Brier/trust rows written from REAL resolutions, and calibration routing
    // ranks the correct agent above the confidently-wrong one.
    const ranking = await calibrationAwareRouting.rankAgents({ domain, candidateAgentIds: [poorAgent, goodAgent] });
    const goodProfile = [...ranking.ranked, ...ranking.demoted].find(p => p.agentId === goodAgent)!;
    const poorProfile = [...ranking.ranked, ...ranking.demoted].find(p => p.agentId === poorAgent)!;
    expect(goodProfile.routingScore).toBeGreaterThan(poorProfile.routingScore);
  }, 30000);

  test('firewall regression: an ordinary DB user cannot resolve', async () => {
    const domain = `b4fw_${Date.now()}`;
    const predId = await registerPrediction(`fw-${crypto.randomUUID().slice(0, 8)}`, domain, 0.8);
    const blocked = await ledgerResolutionService.assertOrdinaryUserCannotResolve(predId);
    expect(blocked).toBe(true);
  });
});
