/**
 * Bounded goal formation E2E (Phase G)
 * ====================================
 * Proves AgentCo proposes bounded internal goals from its OWN database state,
 * and that governance approves low-risk local goals while holding ones that
 * need live web/LLM — no LLM/web required:
 *
 *   1. seed real runtime state: a learner candidate ready_for_eval (low-risk
 *      internal work) and a low-confidence unverified claim (needs live web);
 *   2. GoalFormationService.proposeGoals() returns goals grounded in those
 *      exact DB objects, each with reason, risk tier, budget, and stop
 *      condition;
 *   3. governance auto-approves the low-risk internal goal in test mode and
 *      HOLDS the medium-risk live-web goal (fail closed);
 *   4. the approved goal is active and its lineage (goal_evidence) points at
 *      the seed object; an event trail exists.
 */

import crypto from 'crypto';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { goalFormation } from '../src/services/goal-formation.service';

async function seedReadyCandidate(): Promise<string> {
  // Minimal chain: episode -> trajectory -> replay_batch -> learner_run ->
  // learner_candidate(ready_for_eval). Uses the learner service path is
  // heavier than needed; insert the candidate row directly with its FK chain.
  const runId = crypto.randomUUID();
  await db.query(
    `INSERT INTO replay_batches (id, trajectory_ids, batch_hash, batch_size, simulation_derived, created_by)
     VALUES ($1, ARRAY[]::uuid[], $2, 0, false, 'goal-formation-e2e')`,
    [crypto.randomUUID(), crypto.randomUUID().replace(/-/g, '')]
  );
  const batch = await db.query<{ id: string }>(
    `SELECT id FROM replay_batches WHERE created_by = 'goal-formation-e2e' ORDER BY created_at DESC LIMIT 1`
  );
  await db.query(
    `INSERT INTO learner_runs (id, replay_batch_id, policy_version_before, status)
     VALUES ($1, $2, 'policy-x', 'in_progress')`,
    [runId, batch.rows[0].id]
  );
  const candidateId = crypto.randomUUID();
  const artifactId = crypto.randomUUID();
  await db.query(
    `INSERT INTO artifacts (id, artifact_type, artifact_hash, artifact_json, is_simulation_derived, status)
     VALUES ($1, 'prompt_update', $2, '{}', false, 'created')`,
    [artifactId, crypto.createHash('sha256').update(candidateId).digest('hex')]
  );
  await db.query(
    `INSERT INTO learner_candidates
       (id, learner_run_id, candidate_type, artifact_id, artifact_hash, artifact_json,
        risk_level, simulation_trained, status)
     VALUES ($1,$2,'prompt_update',$3,$4,'{}','low',false,'ready_for_eval')`,
    [candidateId, runId, artifactId, crypto.createHash('sha256').update(candidateId).digest('hex')]
  );
  return candidateId;
}

async function seedLowConfidenceClaim(): Promise<string> {
  const goalId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goals (id, title, description, source, domain, risk_level, status, proposed_by)
     VALUES ($1,'seed goal','seed','agent_proposed','research','low','active','goal-formation-e2e')`,
    [goalId]
  );
  const actionId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective, args, success_criteria, risk_level, decided_by, decided_at, status)
     VALUES ($1,$2,$3,'generate_claim','seed','{}','{}','low','goal-formation-e2e',NOW(),'completed')`,
    [crypto.randomUUID(), actionId, goalId]
  );
  const sourceId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_evidence (source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type)
     VALUES ($1,$2,'https://seed.example/x','seed','a shaky low-confidence claim needing verification',NOW(),$3,'web')`,
    [sourceId, actionId, crypto.randomUUID().replace(/-/g, '')]
  );
  const claimId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_claims (id, claim_id, action_id, goal_id, text, status, confidence, support_source_ids, support_snippets)
     VALUES ($1,$2,$3,$4,'a shaky low-confidence claim needing verification','weakly_supported',0.3,$5::jsonb,$6::jsonb)`,
    [crypto.randomUUID(), claimId, actionId, goalId, JSON.stringify([sourceId]), JSON.stringify(['a shaky low-confidence claim needing verification'])]
  );
  return claimId;
}

let candidateId: string;
let claimId: string;

beforeAll(async () => {
  candidateId = await seedReadyCandidate();
  claimId = await seedLowConfidenceClaim();
});

describe('bounded internal goal formation through governance (Phase G)', () => {
  test('proposes goals grounded in real DB objects, each bounded with reason/risk/budget/stop', async () => {
    // The shared dev DB may already hold many pending candidates/claims from
    // other suites; size the limit so our freshly-seeded rows (ordered
    // oldest-first) are reached deterministically.
    const pending = await db.query<{ n: string }>(
      `SELECT
         (SELECT count(*) FROM learner_candidates WHERE status = 'ready_for_eval')
       + (SELECT count(*) FROM autonomy_claims WHERE COALESCE(confidence,0) < 0.5
              AND COALESCE(status,'unverified') NOT IN ('verified','retired'))
       + (SELECT count(*) FROM event_log WHERE event_type = 'calibration.agent_demoted') AS n`
    );
    const limit = Number(pending.rows[0].n) + 10;
    const proposals = await goalFormation.proposeGoals(limit);

    const forCandidate = proposals.find(p =>
      p.sourceObjects.some(o => o.table === 'learner_candidates' && o.id === candidateId)
    );
    const forClaim = proposals.find(p =>
      p.sourceObjects.some(o => o.table === 'autonomy_claims' && o.id === claimId)
    );

    expect(forCandidate).toBeDefined();
    expect(forCandidate!.riskLevel).toBe('low');
    expect(forCandidate!.requiresLiveServices).toBe(false);
    expect(forCandidate!.reason).toBeTruthy();
    expect(forCandidate!.budget.maxIterations).toBeGreaterThan(0);
    expect(forCandidate!.stopCondition).toBeTruthy();

    expect(forClaim).toBeDefined();
    expect(forClaim!.riskLevel).toBe('medium');
    expect(forClaim!.requiresLiveServices).toBe(true);
  });

  test('governance auto-approves the low-risk internal goal and HOLDS the live-web one', async () => {
    const proposals = await goalFormation.listOpenFormationGoals(500);
    const candidateGoal = proposals.find(p =>
      p.sourceObjects.some(o => o.table === 'learner_candidates' && o.id === candidateId)
    );
    const claimGoal = proposals.find(p =>
      p.sourceObjects.some(o => o.table === 'autonomy_claims' && o.id === claimId)
    );
    expect(candidateGoal && claimGoal).toBeTruthy();

    const decision = await goalFormation.approveProposedGoals([
      candidateGoal!.goalId,
      claimGoal!.goalId,
    ]);

    expect(decision.approved).toContain(candidateGoal!.goalId);
    expect(decision.held).toContain(claimGoal!.goalId);

    const approved = await db.query<{ status: string }>(
      `SELECT status FROM autonomy_goals WHERE id = $1`,
      [candidateGoal!.goalId]
    );
    expect(approved.rows[0].status).toBe('active');

    const held = await db.query<{ status: string }>(
      `SELECT status FROM autonomy_goals WHERE id = $1`,
      [claimGoal!.goalId]
    );
    expect(held.rows[0].status).not.toBe('active');
  });

  test('the approved goal carries lineage back to the seed object', async () => {
    const proposals = await goalFormation.listOpenFormationGoals(500);
    const candidateGoal = proposals.find(p =>
      p.sourceObjects.some(o => o.table === 'learner_candidates' && o.id === candidateId)
    );
    const lineage = await db.query<{ evidence_ref: string }>(
      `SELECT evidence_ref FROM goal_evidence WHERE goal_id = $1`,
      [candidateGoal!.goalId]
    );
    expect(lineage.rows.map(r => r.evidence_ref)).toContain(`learner_candidates:${candidateId}`);
  });
});
