/**
 * Goal-relevant source discovery E2E (Phase B / G4)
 * =================================================
 * The audit's live run fetched arxiv/github/stackoverflow FRONT PAGES for a
 * "Python 3.13 REPL" goal and produced a "grounded" claim about GitHub's
 * marketing copy. This suite proves the replacement, offline:
 *
 *   1. queries are derived from the goal; candidates come from the search
 *      adapter (deterministic fixture backend here — explicitly labeled);
 *   2. relevance is scored BEFORE any fetch, persisted per candidate, and
 *      irrelevant generic homepages are rejected;
 *   3. the fetched source is goal-relevant (a local fixture page standing in
 *      for docs.python.org, served over loopback with the test-only
 *      AGENTCO_ALLOW_LOOPBACK_FETCH flag);
 *   4. a grounded claim ABOUT THE GOAL is accepted with its relevance score;
 *   5. a grounded but OFF-GOAL claim from the same page is downgraded to
 *      weakly_supported — quotability alone no longer makes a finding;
 *   6. the seed-pack fallback applies the same relevance gate: a generic
 *      homepage seed does not survive for an unrelated goal.
 */

import crypto from 'crypto';
import fs from 'fs';
import http from 'http';
import os from 'os';
import path from 'path';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import {
  GoalSourceDiscoveryService,
  RELEVANCE_THRESHOLD,
  CLAIM_RELEVANCE_THRESHOLD,
} from '../src/services/goal-source-discovery.service';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { ActionSpec, ActionStatus, ActionType, RiskLevel } from '../src/types/action.types';

const GOAL_TEXT = 'Summarize what the Python 3.13 release notes say about the new REPL';

const RELEVANT_PAGE = `
  <html><head><title>What's New In Python 3.13</title></head><body>
  <p>The Python 3.13 release notes describe a new interactive REPL with
  multiline editing, colorized tracebacks, and interactive history browsing.
  The new REPL is enabled by default in Python 3.13.</p>
  <p>Separately, the maintainers also enjoy gardening tomatoes on weekends
  and discussing sourdough baking techniques at length.</p>
  </body></html>`;

let server: http.Server;
let baseUrl: string;
let fixtureFile: string;
let goalId: string;
const savedEnv: Record<string, string | undefined> = {};

function makeSpec(actionType: ActionType, args: Record<string, unknown>): ActionSpec {
  return {
    actionId: crypto.randomUUID(),
    actionType,
    objective: `${actionType} for goal-relevance e2e`,
    args: args as any,
    successCriteria: [],
    riskLevel: RiskLevel.LOW,
    decidedBy: 'goal-relevance-e2e',
    decidedAt: new Date(),
    goalId,
  } as unknown as ActionSpec;
}

beforeAll(async () => {
  // Local page standing in for docs.python.org.
  server = http.createServer((req, res) => {
    if (req.url?.startsWith('/whatsnew')) {
      res.writeHead(200, { 'content-type': 'text/html' });
      res.end(RELEVANT_PAGE);
    } else {
      res.writeHead(404);
      res.end('not found');
    }
  });
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  const address = server.address() as { port: number };
  baseUrl = `http://127.0.0.1:${address.port}`;

  // Deterministic fixture search: one goal-relevant result plus a generic
  // homepage that must be rejected by the relevance gate.
  fixtureFile = path.join(os.tmpdir(), `search-fixture-${crypto.randomUUID().slice(0, 8)}.json`);
  fs.writeFileSync(
    fixtureFile,
    JSON.stringify([
      {
        match: ['python', 'repl'],
        results: [
          {
            title: "What's New In Python 3.13 — release notes",
            url: `${baseUrl}/whatsnew`,
            snippet:
              'python 3.13 release notes: the new interactive repl supports multiline editing and colorized tracebacks',
          },
          {
            title: 'GitHub: Let’s build from here',
            url: 'https://github.com/',
            snippet: 'build and ship software on a single collaborative platform',
          },
        ],
      },
    ])
  );

  for (const key of ['AGENTCO_SEARCH_FIXTURE_FILE', 'AGENTCO_ALLOW_LOOPBACK_FETCH']) {
    savedEnv[key] = process.env[key];
  }
  process.env.AGENTCO_SEARCH_FIXTURE_FILE = fixtureFile;
  process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = '1';

  goalId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (
       id, title, description, source, domain, expected_value, risk_level,
       autonomy_level_allowed, status, proposed_by
     ) VALUES ($1,$2,$3,'agent_proposed','research',0.7,'low','L3','approved','goal-relevance-e2e')`,
    [goalId, 'goal relevance e2e', GOAL_TEXT]
  );
});

afterAll(async () => {
  await new Promise<void>(resolve => server.close(() => resolve()));
  fs.rmSync(fixtureFile, { force: true });
  for (const [key, value] of Object.entries(savedEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
});

describe('goal-relevant source discovery (G4)', () => {
  test('accepts the goal-relevant source, rejects the generic homepage, and persists the decision trail', async () => {
    const discovery = new GoalSourceDiscoveryService();
    const result = await discovery.discoverForGoal({ goalId, goalText: GOAL_TEXT, limit: 3 });

    expect(result.searchUsed).toBe(true);
    expect(result.fallbackUsed).toBe(false);
    expect(result.accepted.map(c => c.url)).toContain(`${baseUrl}/whatsnew`);
    expect(result.accepted.map(c => c.url)).not.toContain('https://github.com/');
    const github = result.rejected.find(c => c.url === 'https://github.com/');
    expect(github).toBeDefined();
    expect(github!.relevance).toBeLessThan(RELEVANCE_THRESHOLD);

    const persisted = await db.query<{ url: string; accepted: boolean; relevance_score: string }>(
      `SELECT url, accepted, relevance_score FROM autonomy_source_candidates WHERE goal_id = $1`,
      [goalId]
    );
    expect(persisted.rows.length).toBeGreaterThanOrEqual(2);
    const byUrl = Object.fromEntries(persisted.rows.map(r => [r.url, r]));
    expect(byUrl[`${baseUrl}/whatsnew`].accepted).toBe(true);
    expect(byUrl['https://github.com/'].accepted).toBe(false);
  });

  test('fetching the accepted source yields evidence, and an on-goal grounded claim is accepted with relevance', async () => {
    const executor = new ActionExecutorService();

    const fetchResult = await executor.executeAction(
      makeSpec(ActionType.FETCH_PAGE, { url: `${baseUrl}/whatsnew` })
    );
    expect(fetchResult.status).toBe(ActionStatus.COMPLETED);

    const evidence = await db.query<{ source_id: string; snippet: string }>(
      `SELECT e.source_id, e.snippet
         FROM autonomy_evidence e
         JOIN autonomy_goal_actions a ON a.action_id = e.action_id
        WHERE a.goal_id = $1
        ORDER BY e.created_at DESC LIMIT 1`,
      [goalId]
    );
    expect(evidence.rows.length).toBe(1);
    const { source_id, snippet } = evidence.rows[0];
    expect(snippet.toLowerCase()).toContain('repl');

    // On-goal claim quoting the page.
    const onGoal = 'a new interactive REPL with multiline editing';
    const claimResult = await executor.executeAction(
      makeSpec(ActionType.GENERATE_CLAIM, {
        claimText: onGoal,
        supportSourceIds: [source_id],
        supportSnippets: [onGoal],
      })
    );
    expect(claimResult.status).toBe(ActionStatus.COMPLETED);

    const claim = await db.query<{ status: string; relevance_score: string; relevance_reason: string }>(
      `SELECT status, relevance_score, relevance_reason FROM autonomy_claims WHERE claim_id = $1`,
      [claimResult.observations.claimId]
    );
    expect(claim.rows[0].status).toBe('supported');
    expect(Number(claim.rows[0].relevance_score)).toBeGreaterThanOrEqual(CLAIM_RELEVANCE_THRESHOLD);
  });

  test('a grounded but off-goal claim from the same page is downgraded, not accepted as a finding', async () => {
    const executor = new ActionExecutorService();
    const evidence = await db.query<{ source_id: string }>(
      `SELECT e.source_id
         FROM autonomy_evidence e
         JOIN autonomy_goal_actions a ON a.action_id = e.action_id
        WHERE a.goal_id = $1
        ORDER BY e.created_at DESC LIMIT 1`,
      [goalId]
    );
    const sourceId = evidence.rows[0].source_id;

    const offGoal = 'the maintainers also enjoy gardening tomatoes on weekends';
    const claimResult = await executor.executeAction(
      makeSpec(ActionType.GENERATE_CLAIM, {
        claimText: offGoal,
        supportSourceIds: [sourceId],
        supportSnippets: [offGoal],
      })
    );
    // Grounded (a real quote) — so not blocked — but downgraded.
    expect(claimResult.status).toBe(ActionStatus.COMPLETED);
    expect(claimResult.observations.relevanceDowngrade).toMatch(/off-goal/);

    const claim = await db.query<{ status: string; relevance_score: string }>(
      `SELECT status, relevance_score FROM autonomy_claims WHERE claim_id = $1`,
      [claimResult.observations.claimId]
    );
    expect(claim.rows[0].status).toBe('weakly_supported');
    expect(Number(claim.rows[0].relevance_score)).toBeLessThan(CLAIM_RELEVANCE_THRESHOLD);
  });

  test('seed-pack fallback applies the same relevance gate: generic homepages do not survive', async () => {
    const discovery = new GoalSourceDiscoveryService();
    // Stub the search adapter to fail (as when no backend is configured) so
    // the fallback path runs deterministically without network calls.
    (discovery as any).webAdapter = {
      search: async () => {
        throw new Error('no working search backend (stubbed for offline test)');
      },
    };
    // Stub the seed engine so the fallback path is exercised without live
    // network reachability checks; the stub returns exactly the generic
    // homepage seeds the old code used to fetch unconditionally.
    (discovery as any).seedEngine = {
      discoverSourcesFromPack: async () => [
        {
          source_url: 'https://github.com/trending',
          source_domain: 'github.com',
          source_pack: 'technical',
          topic_hint: 'Trending Repositories',
          discovery_method: 'seed',
        },
        {
          source_url: 'https://arxiv.org/list/cs.AI/recent',
          source_domain: 'arxiv.org',
          source_pack: 'technical',
          topic_hint: 'AI & Computer Science',
          discovery_method: 'seed',
        },
      ],
    };

    const offFixtureGoalId = crypto.randomUUID();
    const result = await discovery.discoverForGoal({
      goalId: offFixtureGoalId,
      goalText: 'catalogue medieval basket weaving techniques of the alpine regions',
      limit: 3,
    });

    expect(result.fallbackUsed).toBe(true);
    expect(result.accepted).toEqual([]);
    expect(result.rejected.length).toBeGreaterThanOrEqual(2);
    for (const rejected of result.rejected) {
      expect(rejected.discoveryMethod).toBe('seed_fallback');
      expect(rejected.reason).toMatch(/rejected/);
    }
    expect(result.note).toMatch(/refusing to fetch generic pages/);
  });
});
