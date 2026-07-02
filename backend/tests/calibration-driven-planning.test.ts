/**
 * Calibration-Driven Planning
 * ===========================
 * Proves calibration history changes runtime routing rather than sitting in
 * the database:
 *   - two agents can do the same work; the planner prefers the one with the
 *     stronger resolved-prediction record
 *   - when the preferred agent's calibration decays, preference flips
 *   - demoted agents are hard-blocked from delegation even if the model
 *     tries to pick them
 *   - decision args carry the calibration inputs, and demotions land in the
 *     event log
 *
 * The LLM fixture deliberately picks the FIRST agent listed in the goal's
 * candidate roster (i.e. it ignores calibration advice). The test passes only
 * because the planner's calibration layer overrides that choice — so the
 * test fails if calibration is ignored.
 */

import crypto from 'crypto';
import fs from 'fs';
import http from 'http';
import path from 'path';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';
import { calibrationAwareRouting } from '../src/services/calibration-aware-routing.service';

const FIXTURE_PORT = 18922;

async function applyMigrations() {
  for (const name of ['009_trust_scores.sql', '079_identity_authority.sql', '080_event_log.sql', '083_transactional_outbox.sql']) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function insertTrustWindow(
  agentId: string,
  domain: string,
  options: { trust: number; brier: number; ece: number; windowEnd?: string; forceDowngrade?: boolean }
): Promise<void> {
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',
             COALESCE($6::timestamptz, NOW()) - INTERVAL '7 days', COALESCE($6::timestamptz, NOW()),
             20, 20, $3, 0.3, $4, $5, $7)`,
    [agentId, domain, options.brier, options.ece, options.trust, options.windowEnd ?? null, options.forceDowngrade ?? false]
  );
}

describe('calibration drives planning and authority', () => {
  let fixtureServer: http.Server;
  const savedEnv: Record<string, string | undefined> = {};
  let rosterFirstAgent = '';

  beforeAll(async () => {
    await applyMigrations();

    // Fixture: always delegates to the FIRST agent in the roster — a model
    // that ignores calibration. Only the planner's enforcement layer can
    // produce a calibrated outcome.
    fixtureServer = http.createServer((req, res) => {
      let body = '';
      req.on('data', chunk => (body += chunk));
      req.on('end', () => {
        const decision = {
          action_type: 'spawn_specialist',
          objective: 'Delegate research to a specialist',
          args: {
            role: 'researcher',
            objective: 'gather evidence',
            goalId: 'set-by-planner',
            assigned_agent_id: rosterFirstAgent,
          },
          reasoning: 'Delegating to the first available agent.',
        };
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ choices: [{ message: { content: JSON.stringify(decision) } }] }));
      });
    });
    await new Promise<void>(resolve => fixtureServer.listen(FIXTURE_PORT, resolve));
    for (const key of ['LLM_BASE_URL', 'LLM_API_KEY', 'OPENAI_API_KEY']) savedEnv[key] = process.env[key];
    process.env.LLM_BASE_URL = `http://127.0.0.1:${FIXTURE_PORT}`;
    process.env.LLM_API_KEY = 'deterministic-test-only';
  });

  afterAll(async () => {
    await new Promise<void>((resolve, reject) => fixtureServer.close(err => (err ? reject(err) : resolve())));
    for (const [key, value] of Object.entries(savedEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  });

  test('ranking prefers the better-calibrated agent and flips when calibration decays', async () => {
    const domain = `calroute_${Date.now()}`;
    const poorAgent = `poor-agent-${crypto.randomUUID().slice(0, 8)}`;
    const goodAgent = `good-agent-${crypto.randomUUID().slice(0, 8)}`;

    await insertTrustWindow(poorAgent, domain, { trust: 0.42, brier: 0.45, ece: 0.25 });
    await insertTrustWindow(goodAgent, domain, { trust: 0.9, brier: 0.08, ece: 0.03 });

    const ranking = await calibrationAwareRouting.rankAgents({
      domain,
      candidateAgentIds: [poorAgent, goodAgent],
    });
    expect(ranking.ranked[0].agentId).toBe(goodAgent);
    expect(ranking.ranked[0].reasonCodes).toContain('well_calibrated');
    const poorProfile =
      ranking.ranked.find(p => p.agentId === poorAgent) ??
      ranking.demoted.find(p => p.agentId === poorAgent)!;
    expect(poorProfile.routingScore).toBeLessThan(ranking.ranked[0].routingScore);
    expect(poorProfile.reasonCodes).toEqual(expect.arrayContaining(['high_brier', 'high_ece']));

    // Calibration decay: a newer bad window for the good agent flips preference.
    await insertTrustWindow(goodAgent, domain, {
      trust: 0.3,
      brier: 0.5,
      ece: 0.3,
      windowEnd: new Date(Date.now() + 60_000).toISOString(),
    });
    const decayed = await calibrationAwareRouting.rankAgents({
      domain,
      candidateAgentIds: [poorAgent, goodAgent],
    });
    expect(decayed.ranked.find(p => p.agentId === goodAgent)).toBeUndefined();
    expect(decayed.demoted.map(p => p.agentId)).toContain(goodAgent);

    // Demotion is auditable.
    const demotionEvents = await db.query(
      `SELECT id FROM event_log
        WHERE event_type = 'calibration.agent_demoted' AND payload->>'agent_id' = $1`,
      [goodAgent]
    );
    expect(demotionEvents.rowCount).toBeGreaterThanOrEqual(1);
  });

  test('planner hard-blocks delegation to demoted agents and records calibration inputs', async () => {
    const domain = `calplan_${Date.now()}`;
    const demotedAgent = `demoted-agent-${crypto.randomUUID().slice(0, 8)}`;
    const calibratedAgent = `calibrated-agent-${crypto.randomUUID().slice(0, 8)}`;
    rosterFirstAgent = demotedAgent; // the model will try to pick this one

    await insertTrustWindow(demotedAgent, domain, {
      trust: 0.2,
      brier: 0.55,
      ece: 0.35,
      forceDowngrade: true,
    });
    await insertTrustWindow(calibratedAgent, domain, { trust: 0.88, brier: 0.09, ece: 0.04 });

    const planner = new AutonomyActionPlannerService();
    const action = await planner.planNextAction(crypto.randomUUID(), {
      goalText: 'Delegate domain research to the most reliable specialist',
      claimsGenerated: 0,
      evidenceCount: 1,
      loopDetection: { isLooping: false } as any,
      memoryContext: '',
      skillContext: '',
      domain,
      candidateAgentIds: [demotedAgent, calibratedAgent],
      previousActions: [],
    });

    // The model chose the demoted agent; the calibration layer overrode it.
    expect(action.args.assigned_agent_id).toBe(calibratedAgent);
    expect(action.args.calibration_override_reason).toContain(demotedAgent);

    // Calibration inputs are part of the decided action (decision log payload).
    expect(action.args.calibration_context).toBeDefined();
    expect(action.args.calibration_context.demoted).toContain(demotedAgent);
    expect(action.args.calibration_context.ranked[0].agent_id).toBe(calibratedAgent);
    expect(action.args.calibration_context.ranked[0].reason_codes).toBeDefined();
  });

  test('agents with no calibration history require verification and rank below proven agents', async () => {
    const domain = `calnew_${Date.now()}`;
    const provenAgent = `proven-agent-${crypto.randomUUID().slice(0, 8)}`;
    const unprovenAgent = `unproven-agent-${crypto.randomUUID().slice(0, 8)}`;
    await insertTrustWindow(provenAgent, domain, { trust: 0.8, brier: 0.1, ece: 0.05 });

    const ranking = await calibrationAwareRouting.rankAgents({
      domain,
      candidateAgentIds: [unprovenAgent, provenAgent],
    });
    expect(ranking.ranked[0].agentId).toBe(provenAgent);
    const unproven = ranking.ranked.find(p => p.agentId === unprovenAgent)!;
    expect(unproven.requiresVerification).toBe(true);
    expect(unproven.reasonCodes).toContain('no_calibration_history');
  });
});
