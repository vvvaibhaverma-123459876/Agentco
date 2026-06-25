/**
 * Evidence extraction — full executor → adapter → extractor → DB path against a real arXiv page.
 *
 * Proves the fix for the raw-HTML evidence bug: a FETCH_PAGE on an arXiv /abs/ page must store
 * CLEAN abstract prose in autonomy_evidence.snippet (no <head>/<title>/HTML tags), not the first
 * 2000 chars of raw HTML.
 *
 * Gated behind RUN_LIVE_SMOKE=1 (needs Postgres + network to arxiv.org). arXiv's search API is
 * flaky/rate-limited, but a direct /abs/ page fetch is reliable, so this validates the storage
 * path independent of the discovery API.
 */
import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { v4 as uuid } from 'uuid';
import { ActionExecutorService } from '../../src/services/action-executor.service';
import { RealWebAdapter } from '../../src/adapters/real-web-adapter';
import { ActionType, RiskLevel } from '../../src/types/action.types';
import { db } from '../../src/db/client';

const RUN = process.env.RUN_LIVE_SMOKE === '1';
const d = RUN ? describe : describe.skip;

d('evidence extraction (real arXiv /abs/ page)', () => {
  const actionId = uuid();
  const goalId = uuid();

  beforeAll(async () => {
    // Parent row for the autonomy_evidence FK (fk_evidence_action → autonomy_goal_actions).
    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1, $2, $3, $4, $5)`,
      [uuid(), actionId, goalId, 'fetch_page', 'fetch arxiv abstract for extraction test'],
    );
  });

  afterAll(async () => {
    // ON DELETE CASCADE removes the evidence rows too.
    await db.query(`DELETE FROM autonomy_goal_actions WHERE action_id = $1`, [actionId]);
    await db.end();
  });

  it('stores a CLEAN abstract (no HTML) for an arXiv /abs/ fetch', async () => {
    const exec = new ActionExecutorService();
    exec.setWebAdapter(new RealWebAdapter());

    const spec = {
      actionId,
      actionType: ActionType.FETCH_PAGE,
      goalId,
      objective: 'fetch abstract',
      args: { url: 'https://arxiv.org/abs/1810.02188' },
      successCriteria: [],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'extraction-test',
      decidedAt: new Date(),
    } as unknown as Parameters<typeof exec.executeAction>[0];

    const res = await exec.executeAction(spec);
    expect(res.status).toBe('completed');

    const rows = await db.query(
      `SELECT snippet FROM autonomy_evidence WHERE action_id = $1 ORDER BY created_at DESC LIMIT 1`,
      [actionId],
    );
    expect(rows.rows.length).toBe(1);
    const snippet: string = rows.rows[0].snippet;

    // Clean: no HTML tags, no <head>/<title>, no CSS chunk refs.
    expect(snippet).not.toMatch(/<[a-z]/i);
    expect(snippet.toLowerCase()).not.toContain('<title');
    expect(snippet).not.toContain('_next/static');
    // Real abstract prose from the paper (1810.02188 is about primes of the form 6^{m+1}.N - 1).
    expect(snippet.toLowerCase()).toMatch(/we show that|prime number for any/);
  }, 30000);
});
