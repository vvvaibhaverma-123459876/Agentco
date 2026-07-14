import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { identityAuthorityService } from '../src/services/identity-authority.service';
import { civilizationKernel } from '../src/services/civilization-kernel.service';
import { safeEvolution } from '../src/services/safe-evolution.service';
import { missionService } from '../src/services/mission.service';

async function applyMigrations() {
  for (const file of [
    '129_civilization_kernel.sql', '130_citizenship.sql',
    '131_societies_and_institution_charters.sql', '132_institution_coalitions.sql',
    '133_missions.sql', '134_civilization_economy.sql', '135_governance.sql', '136_judiciary.sql',
    '137_collective_epistemics.sql', '138_safe_evolution.sql',
  ]) {
    await migrationDb.query(fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${file}`), 'utf8'));
  }
}

async function actor(prefix: string): Promise<string> {
  const a = await identityAuthorityService.registerActor({
    actor_type: 'human', name: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 1e6)}`,
  });
  return a.id;
}

/** Drive a candidate proposed -> approved with an independent passing evaluation. */
async function driveToApproved(proposer: string, evaluator: string, tier = 2): Promise<string> {
  const candidate = await safeEvolution.createCandidate({
    source: 'benchmark', learning_form: 'skill', title: `Cand ${Date.now()}-${Math.random()}`,
    hypothesis: 'improves success rate', proposer_actor_id: proposer, tier,
  });
  await safeEvolution.recordFailureAnalysis({
    candidate_id: candidate.id, failure_summary: 'benchmark gap', root_cause: 'weak planning', analysed_by_actor_id: proposer,
  });
  const gen = await safeEvolution.generateRegressions({ candidate_id: candidate.id, actor_id: proposer });
  await safeEvolution.markSandboxed({ candidate_id: candidate.id, actor_id: proposer });
  await safeEvolution.evaluate({
    candidate_id: candidate.id, evaluator_actor_id: evaluator, cases_passed: gen.count,
    safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true,
  });
  return candidate.id;
}

describe('learning and safe evolution (C10)', () => {
  beforeAll(async () => {
    await applyMigrations();
    await civilizationKernel.ensureCivilizationRoot();
  });

  test('SCENARIO E: failure -> candidate -> regressions -> sandbox -> independent eval -> canary -> promote; rollback path works', async () => {
    const proposer = await actor('evo-proposer');
    const evaluator = await actor('evo-evaluator');
    const approver = await actor('evo-approver');

    const candidateId = await driveToApproved(proposer, evaluator);
    let c = await safeEvolution.getCandidate(candidateId);
    expect(c!.status).toBe('approved');
    expect(c!.regression_cases).toBe(4);

    const canary = await safeEvolution.startCanary({ candidate_id: candidateId, actor_id: proposer });
    await safeEvolution.reportCanary({ canary_id: canary.canary_id, actor_id: proposer, clean: true, metric: { latency_ms: 40 } });

    // Tier-2 needs a human approver distinct from the proposer.
    await expect(safeEvolution.promote({ candidate_id: candidateId, actor_id: proposer, artifact_hash: 'h1', human_approved: true }))
      .rejects.toThrow(/proposer cannot approve their own promotion/);
    await expect(safeEvolution.promote({ candidate_id: candidateId, actor_id: approver, artifact_hash: 'h1' }))
      .rejects.toThrow(/require human approval/);

    const promotion = await safeEvolution.promote({ candidate_id: candidateId, actor_id: approver, artifact_hash: 'h1', human_approved: true });
    expect(promotion.version).toBe(1);
    c = await safeEvolution.getCandidate(candidateId);
    expect(c!.status).toBe('monitored');
    expect(c!.lineage).toBe(1);

    // Rollback path from monitored.
    const rb = await safeEvolution.rollback({ candidate_id: candidateId, actor_id: approver, reason: 'post-promotion regression' });
    expect(rb.version).toBe(2);
    const after = await safeEvolution.getCandidate(candidateId);
    expect(after!.status).toBe('rolled_back');
    expect(after!.lineage).toBe(2); // promote + rollback both recorded in lineage

    // Terminal candidate is immutable.
    await expect(
      db.query(`UPDATE civ_learning_candidates SET status = 'monitored' WHERE id = $1`, [candidateId])
    ).rejects.toThrow(/SAFE-EVOLUTION GUARD/);
  });

  test('independent evaluation is enforced: the evaluator cannot be the proposer', async () => {
    const proposer = await actor('evo-selfeval');
    const candidate = await safeEvolution.createCandidate({
      source: 'audit', learning_form: 'policy', title: `Self ${Date.now()}`,
      hypothesis: 'x', proposer_actor_id: proposer,
    });
    await safeEvolution.recordFailureAnalysis({ candidate_id: candidate.id, failure_summary: 's', root_cause: 'r', analysed_by_actor_id: proposer });
    await safeEvolution.generateRegressions({ candidate_id: candidate.id, actor_id: proposer });
    await safeEvolution.markSandboxed({ candidate_id: candidate.id, actor_id: proposer });
    await expect(safeEvolution.evaluate({
      candidate_id: candidate.id, evaluator_actor_id: proposer, cases_passed: 4,
      safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true,
    })).rejects.toThrow(/evaluator cannot be the proposer/);
  });

  test('a regression or safety failure rejects the candidate', async () => {
    const proposer = await actor('evo-fail');
    const evaluator = await actor('evo-fail-eval');
    const candidate = await safeEvolution.createCandidate({
      source: 'safety_incident', learning_form: 'calibration_threshold', title: `Bad ${Date.now()}`,
      hypothesis: 'x', proposer_actor_id: proposer,
    });
    await safeEvolution.recordFailureAnalysis({ candidate_id: candidate.id, failure_summary: 's', root_cause: 'r', analysed_by_actor_id: proposer });
    const gen = await safeEvolution.generateRegressions({ candidate_id: candidate.id, actor_id: proposer });
    await safeEvolution.markSandboxed({ candidate_id: candidate.id, actor_id: proposer });
    const result = await safeEvolution.evaluate({
      candidate_id: candidate.id, evaluator_actor_id: evaluator, cases_passed: gen.count - 1, // one case failed
      safety_non_regression: true, calibration_non_regression: true, evidence_non_regression: true,
    });
    expect(result.passed).toBe(false);
    const c = await safeEvolution.getCandidate(candidate.id);
    expect(c!.status).toBe('rejected');
  });

  test('a breached canary forces rollback and blocks promotion', async () => {
    const proposer = await actor('evo-canary');
    const evaluator = await actor('evo-canary-eval');
    const candidateId = await driveToApproved(proposer, evaluator, 1); // Tier-1
    const canary = await safeEvolution.startCanary({ candidate_id: candidateId, actor_id: proposer });
    await safeEvolution.reportCanary({ canary_id: canary.canary_id, actor_id: proposer, clean: false, breach_reason: 'latency spike' });

    const c = await safeEvolution.getCandidate(candidateId);
    expect(c!.status).toBe('rolled_back');
    await expect(safeEvolution.promote({ candidate_id: candidateId, actor_id: proposer, artifact_hash: 'h' }))
      .rejects.toThrow(/requires a canary candidate/);
  });

  test('Tier-1 clean-canary candidate can promote without a separate human approver', async () => {
    const proposer = await actor('evo-tier1');
    const evaluator = await actor('evo-tier1-eval');
    const candidateId = await driveToApproved(proposer, evaluator, 1);
    const canary = await safeEvolution.startCanary({ candidate_id: candidateId, actor_id: proposer });
    await safeEvolution.reportCanary({ canary_id: canary.canary_id, actor_id: proposer, clean: true });
    const promo = await safeEvolution.promote({ candidate_id: candidateId, actor_id: proposer, artifact_hash: 't1' });
    expect(promo.version).toBe(1);
  });

  test('a failed mission automatically creates a task_failure learning candidate', async () => {
    const missionActor = await actor('evo-mission');
    const mission = await missionService.createMission({ title: `Doomed ${Date.now()}`, actor_id: missionActor });
    for (const [to, reason] of [['triaged', 't'], ['approved', 'a'], ['funded', 'f'], ['planned', 'p'], ['assigned', 'x'], ['executing', 'go']] as Array<[string, string]>) {
      await missionService.transitionMission({ mission_id: mission.id, to_status: to as any, actor_id: missionActor, reason });
    }
    await missionService.transitionMission({ mission_id: mission.id, to_status: 'failed', actor_id: missionActor, reason: 'unrecoverable error' });

    const candidate = await db.query(
      `SELECT id, source, learning_form FROM civ_learning_candidates WHERE source_mission_id = $1 AND source = 'task_failure'`,
      [mission.id]
    );
    expect(candidate.rowCount).toBe(1);
    expect(candidate.rows[0].learning_form).toBe('planning');
  });
});
