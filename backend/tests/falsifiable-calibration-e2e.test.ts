/**
 * Falsifiable calibration E2E (G2 / G3)
 * =====================================
 * The audit's core finding: predictions were registered at constant p=0.8,
 * dated in the past, and resolved TRUE from the claim's own snippet — the
 * system could not be wrong, so calibration measured nothing.
 *
 * This suite proves the replacement loop with zero LLM/web access:
 *   1. probabilities are derived, not constant;
 *   2. a prediction resolves TRUE only from an INDEPENDENT source;
 *   3. same-source/same-host evidence is refused (auditable), prediction
 *      stays open;
 *   4. a prediction with no corroboration stays OPEN before its due time;
 *   5. an overdue uncorroborated prediction resolves FALSE — the system is
 *      wrong, on the record;
 *   6. a false outcome worsens Brier/trust and routing rank relative to an
 *      agent whose prediction resolved true.
 */

import crypto from 'crypto';
import { Pool } from 'pg';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { falsifiablePrediction } from '../src/services/falsifiable-prediction.service';
import { independentResolver } from '../src/services/independent-resolver.service';
import { calibrationAwareRouting } from '../src/services/calibration-aware-routing.service';

const DOMAIN = 'autonomy_research';

let servicePool: Pool;
let goalId: string;

async function seedGoal(): Promise<string> {
  const id = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (
       id, title, description, source, domain, expected_value, risk_level,
       autonomy_level_allowed, status, proposed_by
     ) VALUES ($1,$2,$3,'agent_proposed','research',0.7,'low','L3','approved','falsifiable-e2e')`,
    [id, 'falsifiable calibration e2e', 'seeded goal for deterministic resolution tests']
  );
  return id;
}

async function seedEvidence(url: string, snippet: string): Promise<string> {
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goal_actions (
       id, action_id, goal_id, action_type, objective, args, success_criteria,
       risk_level, decided_by, decided_at, reasoning, status
     ) VALUES ($1,$2,$3,'fetch_page','seed evidence','{}','{}','low','falsifiable-e2e',NOW(),'seed','completed')`,
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

describe('falsifiable predictions (G2)', () => {
  test('probability is derived from context, never the constant 0.8', async () => {
    const oneSource = await seedEvidence('https://host-a.example/page1', 'python added a new colorized repl in the latest release');
    const s1 = await seedEvidence('https://host-b.example/p', 'independent snippet one about the colorized repl');
    const s2 = await seedEvidence('https://host-c.example/p', 'independent snippet two about the colorized repl');

    const thin = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'python added a new colorized repl',
      supportSourceIds: [oneSource],
      producingAgentId: `falsifiable-thin-${crypto.randomUUID().slice(0, 8)}`,
      domain: DOMAIN,
      runId: 'test-run',
    });
    const rich = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText:
        'the python 3.13 interactive interpreter gained multiline editing colorized tracebacks and history browsing support',
      supportSourceIds: [oneSource, s1, s2],
      producingAgentId: `falsifiable-rich-${crypto.randomUUID().slice(0, 8)}`,
      domain: DOMAIN,
      runId: 'test-run',
    });

    expect(thin.probability).not.toBe(0.8);
    expect(rich.probability).not.toBe(0.8);
    expect(rich.probability).toBeGreaterThan(thin.probability);
    // Due time is in the future by default.
    expect(thin.resolutionDate.getTime()).toBeGreaterThan(Date.now());
  });

  test('resolves TRUE only from an independent host, never from the claim source', async () => {
    const agent = `falsifiable-true-${crypto.randomUUID().slice(0, 8)}`;
    const own = await seedEvidence(
      'https://docs-mirror.example/notes',
      'the release notes describe the improved interactive shell with multiline editing support'
    );
    const prediction = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'the release notes describe the improved interactive shell with multiline editing',
      supportSourceIds: [own],
      producingAgentId: agent,
      domain: DOMAIN,
      runId: 'test-run',
      dueInMs: 50, // short maturity so the test can resolve after the time gate
    });

    // Independent corroboration from a DIFFERENT host.
    await seedEvidence(
      'https://independent-review.example/article',
      'reviewers confirmed the improved interactive shell now offers multiline editing in the release notes'
    );
    await new Promise(resolve => setTimeout(resolve, 120)); // pass maturity

    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: prediction.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(outcome.status).toBe('resolved_true');
      expect(outcome.brierScore).toBeCloseTo(Math.pow(prediction.probability - 1, 2), 5);
      expect(outcome.trustFactor).not.toBeNull();
    } finally {
      client.release();
    }
  });

  test('refuses same-source/same-host self-confirmation; prediction stays open (auditable)', async () => {
    const agent = `falsifiable-refuse-${crypto.randomUUID().slice(0, 8)}`;
    const own = await seedEvidence(
      'https://lonely-host.example/only',
      'a very unusual assertion zebra quartz nebula that appears nowhere else'
    );
    // A second row from the SAME host must not count as independent.
    await seedEvidence(
      'https://lonely-host.example/again',
      'a very unusual assertion zebra quartz nebula that appears nowhere else repeated'
    );
    const prediction = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'unusual assertion zebra quartz nebula appears nowhere else',
      supportSourceIds: [own],
      producingAgentId: agent,
      domain: DOMAIN,
      runId: 'test-run',
    });

    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: prediction.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(['refused', 'open']).toContain(outcome.status);
      const row = await db.query<{ resolved: boolean }>(
        `SELECT resolved FROM prediction_ledger WHERE prediction_id = $1`,
        [prediction.predictionId]
      );
      expect(row.rows[0].resolved).toBe(false);
    } finally {
      client.release();
    }
  });

  test('stays OPEN before the due time when no independent evidence exists', async () => {
    const own = await seedEvidence(
      'https://another-host.example/x',
      'completely unique statement crimson falcon delta without corroboration'
    );
    const prediction = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'unique statement crimson falcon delta without corroboration',
      supportSourceIds: [own],
      producingAgentId: `falsifiable-open-${crypto.randomUUID().slice(0, 8)}`,
      domain: DOMAIN,
      runId: 'test-run',
      dueInMs: 60 * 60 * 1000,
    });
    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: prediction.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(['open', 'refused']).toContain(outcome.status);
    } finally {
      client.release();
    }
  });
});

describe('the system can be wrong, and it costs trust (G2/G3)', () => {
  const agentRight = `agent-right-${crypto.randomUUID().slice(0, 8)}`;
  const agentWrong = `agent-wrong-${crypto.randomUUID().slice(0, 8)}`;
  let rightTrust: number;
  let wrongTrust: number;

  test('an overdue uncorroborated prediction resolves FALSE via the sweep', async () => {
    const own = await seedEvidence(
      'https://wrong-source.example/claim',
      'bold assertion emerald walrus sonata that nobody will ever corroborate'
    );
    const prediction = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'bold assertion emerald walrus sonata nobody will corroborate',
      supportSourceIds: [own],
      producingAgentId: agentWrong,
      domain: DOMAIN,
      runId: 'test-run',
      dueInMs: -1000, // already overdue
      historicalRegistrationReason: 'deterministic overdue falsifiable-calibration fixture',
    });

    const client = await servicePool.connect();
    try {
      const sweep = await independentResolver.resolveDuePredictions({
        serviceClient: client,
        producingAgentId: agentWrong,
      });
      expect(sweep.resolvedFalse).toBeGreaterThanOrEqual(1);
    } finally {
      client.release();
    }

    const row = await db.query<{ resolved: boolean; resolved_outcome: boolean; brier_score: string }>(
      `SELECT resolved, resolved_outcome, brier_score FROM prediction_ledger WHERE prediction_id = $1`,
      [prediction.predictionId]
    );
    expect(row.rows[0].resolved).toBe(true);
    expect(row.rows[0].resolved_outcome).toBe(false);
    // Brier for a false outcome at probability p is p^2 — a real penalty.
    expect(Number(row.rows[0].brier_score)).toBeCloseTo(Math.pow(prediction.probability, 2), 4);

    const trust = await db.query<{ trust_factor: string }>(
      `SELECT trust_factor FROM trust_scores WHERE subject_id = $1 ORDER BY computed_at DESC LIMIT 1`,
      [agentWrong]
    );
    wrongTrust = Number(trust.rows[0].trust_factor);
  });

  test('a true outcome earns more trust than a false one, and routing prefers the right agent', async () => {
    const own = await seedEvidence(
      'https://right-source.example/claim',
      'verified assertion amber falcon sonata corroborated elsewhere in detail'
    );
    const prediction = await falsifiablePrediction.registerForClaim({
      claimId: crypto.randomUUID(),
      claimText: 'verified assertion amber falcon sonata corroborated elsewhere',
      supportSourceIds: [own],
      producingAgentId: agentRight,
      domain: DOMAIN,
      runId: 'test-run',
      dueInMs: 50,
    });
    await seedEvidence(
      'https://corroborator.example/review',
      'our review found the verified assertion amber falcon sonata corroborated elsewhere as stated'
    );
    await new Promise(resolve => setTimeout(resolve, 120)); // pass maturity

    const client = await servicePool.connect();
    try {
      const outcome = await independentResolver.attemptResolution({
        predictionId: prediction.predictionId,
        serviceClient: client,
        goalId,
      });
      expect(outcome.status).toBe('resolved_true');
    } finally {
      client.release();
    }

    const trust = await db.query<{ trust_factor: string }>(
      `SELECT trust_factor FROM trust_scores WHERE subject_id = $1 ORDER BY computed_at DESC LIMIT 1`,
      [agentRight]
    );
    rightTrust = Number(trust.rows[0].trust_factor);

    // Calibration moved in BOTH directions and it changes routing authority.
    expect(rightTrust).toBeGreaterThan(wrongTrust);

    const ranking = await calibrationAwareRouting.rankAgents({
      domain: DOMAIN,
      candidateAgentIds: [agentRight, agentWrong],
    });
    const score = (id: string) =>
      ranking.ranked.find(p => p.agentId === id)?.routingScore ??
      ranking.demoted.find(p => p.agentId === id)?.routingScore ?? -1;
    expect(score(agentRight)).toBeGreaterThan(score(agentWrong));
  });
});
