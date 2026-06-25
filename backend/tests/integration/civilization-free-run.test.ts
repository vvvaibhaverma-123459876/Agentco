/**
 * Civilization Free-Run — real assertions against the vision's Definition of Done.
 * Gated RUN_LIVE_SMOKE=1 (needs Postgres). Fixture mode => no LLM/web, deterministic.
 *
 * Covers DoD: runs without a user goal (#2,3), routes to a society agenda (#4), executes a
 * bounded task producing a claim (#5,6), promotes a grounded claim through the gate (#7),
 * BLOCKS an unverified claim (#8), registers a prediction (#9), writes a report artifact (#11).
 */
import { describe, it, expect, afterAll } from '@jest/globals';
import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid';
import { CivilizationFreeRunService } from '../../src/services/civilization-free-run.service';
import { db } from '../../src/db/client';

const RUN = process.env.RUN_LIVE_SMOKE === '1';
const d = RUN ? describe : describe.skip;

d('civilization free-run (fixture, real Postgres)', () => {
  const svc = new CivilizationFreeRunService();

  afterAll(async () => { await db.end(); });

  it('runs WITHOUT a user goal and completes the full vision loop', async () => {
    const report = await svc.run('fixture');

    // #2/#3 internal goal generated from self-assessment, no user prompt.
    expect(report.weaknesses.length).toBeGreaterThan(0);
    expect(report.internalGoalId).toBeTruthy();
    const goal = await db.query(`SELECT source, proposed_by FROM autonomy_goals WHERE id = $1`, [report.internalGoalId]);
    expect(goal.rows[0].proposed_by).toBe('civilization_free_run');
    expect(goal.rows[0].source).toBe('perception_derived'); // internally derived, not user

    // #4 routed to a society agenda (persisted).
    expect(report.agendaItemId).toBeTruthy();
    expect(report.societyId).toMatch(/society/);

    // #5/#6/#7 bounded task produced a claim and the gate PROMOTED the grounded one.
    expect(report.claimsProcessed).toBe(1);
    expect(report.claimsPromoted).toBe(1);
    expect(report.claimsBlocked).toBe(0);

    // #9 a prediction was registered for the promoted (now-trusted) claim.
    expect(report.predictionsRegistered).toBe(1);

    // #11 report artifact written.
    const md = path.join(report.reportDir, 'civilization_report.md');
    expect(fs.existsSync(md)).toBe(true);
    expect(fs.readFileSync(md, 'utf8')).toMatch(/Civilization Free-Run Report/);
  }, 30000);

  it('#8 BLOCKS an unverified claim (snippet not traceable to its cited source)', async () => {
    // Set up a claim whose support snippet is NOT in its evidence => promotion must block it.
    const sourceId = uuid(), actionId = uuid(), claimId = uuid();
    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim','free-run negative test')`, [uuid(), actionId, uuid()]);
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,'web',true,NOW())`,
      [uuid(), sourceId, actionId, 'https://example.com/x', 'X', 'This abstract is about photosynthesis in plants.', 'h']);
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7)`,
      [uuid(), claimId, actionId, 'The Riemann hypothesis was proven using prime sieves.',
       JSON.stringify([sourceId]), JSON.stringify(['prime sieves prove the Riemann hypothesis']), JSON.stringify([actionId])]);

    const gate = await svc.promotionGate([claimId]);
    expect(gate.blocked).toContain(claimId);
    expect(gate.promoted).not.toContain(claimId);

    const row = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
    expect(row.rows[0].status).toBe('supported'); // NOT promoted

    await db.query(`DELETE FROM autonomy_goal_actions WHERE action_id = $1`, [actionId]);
  }, 20000);
});
