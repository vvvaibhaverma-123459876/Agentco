/**
 * Working Eyes (B2 / GA2)
 * =======================
 * A real fetch of a page must produce hashed evidence that a grounded claim
 * can cite — with NO search backend configured. Uses a real local HTTP
 * server (real network fetch through the real adapter + SSRF guard), so this
 * is genuine evidence acquisition, not a mock.
 *
 * Also proves: honest search-backend reporting (no silent empty success), and
 * the grounding gate still rejects a fabricated claim citing fetched content.
 */

import crypto from 'crypto';
import fs from 'fs';
import http from 'http';
import path from 'path';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { RealWebAdapter } from '../src/adapters/real-web-adapter';
import { claimGrounding } from '../src/services/claim-grounding.service';
import { ActionType, ActionStatus, RiskLevel } from '../src/types/action.types';

const PORT = 18944;
const FACT = 'The Zephyr-9 turbine sustains 4200 rpm under rated load without vibration faults.';

async function applyMigrations() {
  for (const name of ['004_decision_log.sql', '050_autonomy_action_loop.sql', '079_identity_authority.sql']) {
    await db.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8'));
  }
}

async function makeAction(): Promise<string> {
  const goalId = crypto.randomUUID();
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (id,title,description,source,domain,expected_value,risk_level,autonomy_level_allowed,status,proposed_by)
     VALUES ($1,'t','t','agent_proposed','eyes',0.5,'low','L3','approved','audit')`,
    [goalId]
  );
  await db.query(
    `INSERT INTO autonomy_goal_actions (id,action_id,goal_id,action_type,objective,args,success_criteria,risk_level,decided_by,decided_at,status)
     VALUES ($1,$2,$3,'fetch_page','fetch','{}','[]','low','audit',NOW(),'planned')`,
    [crypto.randomUUID(), actionId, goalId]
  );
  return actionId;
}

describe('working eyes (B2)', () => {
  let server: http.Server;
  const saved: Record<string, string | undefined> = {};

  beforeAll(async () => {
    await applyMigrations();
    server = http.createServer((_req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(`<!doctype html><html><head><title>Zephyr Spec</title></head><body><p>${FACT}</p></body></html>`);
    });
    await new Promise<void>(r => server.listen(PORT, r));
    saved.AGENTCO_ALLOW_LOOPBACK_FETCH = process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = '1'; // fixture is loopback
  });

  afterAll(async () => {
    await new Promise<void>((r, j) => server.close(e => (e ? j(e) : r())));
    if (saved.AGENTCO_ALLOW_LOOPBACK_FETCH === undefined) delete process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    else process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = saved.AGENTCO_ALLOW_LOOPBACK_FETCH;
  });

  test('a bare executor fetches a real page and produces hashed evidence with no search backend', async () => {
    // A bare executor (no setWebAdapter) must still be able to fetch — proving
    // the direct-fetch path works with zero configuration.
    const executor = new ActionExecutorService();
    const actionId = await makeAction();
    const result = await executor.executeAction({
      actionId,
      actionType: ActionType.FETCH_PAGE,
      goalId: undefined,
      objective: 'Fetch the spec page',
      args: { url: `http://127.0.0.1:${PORT}/spec` },
      successCriteria: ['fetched'],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'audit',
      decidedAt: new Date(),
    });
    expect(result.status).toBe(ActionStatus.COMPLETED);
    expect(result.createdArtifacts.length).toBeGreaterThan(0);

    const sourceId = result.createdArtifacts[0];
    const ev = await db.query<{ content_hash: string; url: string; snippet: string }>(
      `SELECT content_hash, url, snippet FROM autonomy_evidence WHERE source_id = $1`,
      [sourceId]
    );
    expect(ev.rowCount).toBe(1);
    expect(ev.rows[0].content_hash).toMatch(/^sha256:/);
    expect(ev.rows[0].url).toContain(`127.0.0.1:${PORT}`);
    expect(ev.rows[0].snippet).toContain('Zephyr-9 turbine');

    // A grounded claim citing the fetched evidence passes the gate...
    const grounded = await claimGrounding.validate({
      claimText: 'The Zephyr-9 turbine sustains 4200 rpm.',
      supportSourceIds: [sourceId],
      supportSnippets: ['the zephyr 9 turbine sustains 4200 rpm under rated load'],
    });
    expect(grounded.valid).toBe(true);

    // ...and a fabricated claim citing the same evidence is rejected.
    const fabricated = await claimGrounding.validate({
      claimText: 'The Zephyr-9 turbine explodes at 4200 rpm.',
      supportSourceIds: [sourceId],
      supportSnippets: ['the zephyr 9 turbine explodes and is dangerous'],
    });
    expect(fabricated.valid).toBe(false);
  });

  test('fetch_page is SSRF-blocked for private / metadata targets even with default adapter', async () => {
    const executor = new ActionExecutorService();
    const savedLoopback = process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    delete process.env.AGENTCO_ALLOW_LOOPBACK_FETCH; // no loopback exception here
    try {
      for (const url of ['http://169.254.169.254/latest/meta-data', 'http://10.0.0.1/', 'http://127.0.0.1/', 'file:///etc/passwd']) {
        const actionId = await makeAction();
        const result = await executor.executeAction({
          actionId,
          actionType: ActionType.FETCH_PAGE,
          goalId: undefined,
          objective: 'fetch',
          args: { url },
          successCriteria: ['f'],
          riskLevel: RiskLevel.LOW,
          decidedBy: 'audit',
          decidedAt: new Date(),
        });
        expect(result.status).toBe(ActionStatus.BLOCKED);
        expect(result.createdArtifacts.length).toBe(0);
      }
    } finally {
      if (savedLoopback === undefined) delete process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
      else process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = savedLoopback;
    }
  });

  test('search backend availability is reported honestly (no silent empty success)', async () => {
    const adapter = new RealWebAdapter();
    const availability = adapter.availableSearchBackends();
    // With no keys configured, every keyed backend is reported unavailable.
    expect(availability.searxng.configured).toBe(false);
    expect(availability.google.configured).toBe(false);
    expect(availability.bing.configured).toBe(false);
    // And a search with no backend fails with an actionable error naming env vars.
    const saveKeys = {
      SEARXNG_URL: process.env.SEARXNG_URL,
      SEARCH_ENGINE_API_KEY: process.env.SEARCH_ENGINE_API_KEY,
      BING_SEARCH_API_KEY: process.env.BING_SEARCH_API_KEY,
    };
    delete process.env.SEARXNG_URL;
    delete process.env.SEARCH_ENGINE_API_KEY;
    delete process.env.BING_SEARCH_API_KEY;
    process.env.AGENTCO_DISABLE_DDG = '1'; // avoid the flaky scraper in CI
    try {
      await expect(adapter.search('anything')).rejects.toThrow(/SEARXNG_URL|SEARCH_ENGINE_API_KEY|BING_SEARCH_API_KEY|fetch_page/);
    } finally {
      for (const [k, v] of Object.entries(saveKeys)) {
        if (v === undefined) delete (process.env as any)[k];
        else (process.env as any)[k] = v;
      }
      delete process.env.AGENTCO_DISABLE_DDG;
    }
  });
});
