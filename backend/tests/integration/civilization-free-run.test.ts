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
    expect(report.institutionId).toBeTruthy();
    expect(report.taskType).toMatch(/promote_supported_claims|ingest_research_evidence/);
    const agenda = await db.query(`SELECT content FROM autonomy_memory WHERE id = $1`, [report.agendaItemId]);
    expect(agenda.rows[0].content.societyId).toBe(report.societyId);
    expect(agenda.rows[0].content.institutionId).toBe(report.institutionId);
    expect(agenda.rows[0].content.taskType).toBe(report.taskType);

    // #5/#6/#7 bounded task produced a claim and the gate PROMOTED the grounded one.
    expect(report.claimsProcessed).toBe(1);
    expect(report.claimsPromoted).toBe(1);
    expect(report.claimsBlocked).toBe(0);
    const action = await db.query(
      `SELECT objective FROM autonomy_goal_actions WHERE goal_id = $1 ORDER BY created_at DESC LIMIT 1`,
      [report.internalGoalId]
    );
    expect(action.rows[0].objective).toContain(report.societyId);
    expect(action.rows[0].objective).toContain(report.institutionId);

    // #9 a prediction was registered for the promoted (now-trusted) claim.
    expect(report.predictionsRegistered).toBe(1);

    // #11 report artifact written.
    const md = path.join(report.reportDir, 'civilization_report.md');
    expect(fs.existsSync(md)).toBe(true);
    expect(fs.readFileSync(md, 'utf8')).toMatch(/Civilization Free-Run Report/);
    const claimsJsonl = path.join(report.reportDir, 'claims.jsonl');
    expect(fs.existsSync(claimsJsonl)).toBe(true);
    expect(fs.readFileSync(claimsJsonl, 'utf8')).toMatch(/claim_id/);
    const eventsJsonl = path.join(report.reportDir, 'events.jsonl');
    expect(fs.existsSync(eventsJsonl)).toBe(true);
    expect(fs.readFileSync(eventsJsonl, 'utf8')).toMatch(/society_agenda/);
  }, 30000);

  it('uses the society agenda to drive the fixture bounded task route', async () => {
    const calibrationWeakness = {
      kind: 'unpromoted_knowledge',
      detail: 'supported claims need promotion',
      recommendedGoal: {
        title: 'Promote supported claims',
        description: 'Run the promotion gate.',
        domain: 'calibration',
      },
    };
    const researchWeakness = {
      kind: 'thin_evidence',
      detail: 'knowledge base has too few claims',
      recommendedGoal: {
        title: 'Gather research evidence',
        description: 'Ingest grounded research.',
        domain: 'research',
      },
    };

    const calibrationGoalId = await svc.generateInternalGoal(calibrationWeakness);
    const researchGoalId = await svc.generateInternalGoal(researchWeakness);
    const calibrationAgenda = await svc.createAgendaItem(calibrationGoalId, calibrationWeakness);
    const researchAgenda = await svc.createAgendaItem(researchGoalId, researchWeakness);

    expect(calibrationAgenda.societyId).toBe('calibration_society');
    expect(calibrationAgenda.institutionId).toBe('evidence_promotion_institution');
    expect(calibrationAgenda.taskType).toBe('promote_supported_claims');
    expect(researchAgenda.societyId).toBe('scientific_society');
    expect(researchAgenda.institutionId).toBe('research_ingestion_institution');
    expect(researchAgenda.taskType).toBe('ingest_research_evidence');

    const [calibrationClaimId] = await svc.executeBoundedTaskFixture(calibrationGoalId, calibrationAgenda);
    const [researchClaimId] = await svc.executeBoundedTaskFixture(researchGoalId, researchAgenda);

    const rows = await db.query(
      `SELECT g.goal_id, g.objective, c.claim_id, c.text
         FROM autonomy_goal_actions g
         JOIN autonomy_claims c ON c.action_id = g.action_id
        WHERE c.claim_id = ANY($1)
        ORDER BY c.generated_at ASC`,
      [[calibrationClaimId, researchClaimId]]
    );
    const byClaim = new Map(rows.rows.map((r: { claim_id: string; objective: string; text: string }) => [r.claim_id, r]));
    expect(byClaim.get(calibrationClaimId)!.objective).toContain('calibration_society/evidence_promotion_institution');
    expect(byClaim.get(calibrationClaimId)!.text).toContain('Calibration improves');
    expect(byClaim.get(researchClaimId)!.objective).toContain('scientific_society/research_ingestion_institution');
    expect(byClaim.get(researchClaimId)!.text).toContain('Bounded gaps between primes');
  }, 20000);

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
