import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { LearnerService } from '../src/services/learner.service';
import { proofOfCompetence } from '../src/services/proof-of-competence.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';
import { skillLibrary } from '../src/services/skill-library.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '104_candidate_regression_tests.sql',
    '105_skill_library.sql',
    '106_proof_of_competence.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function createTrajectory(successful: boolean, traceId: string): Promise<string> {
  const episodeId = crypto.randomUUID();
  const trajectoryId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_episodes
       (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status,
        reward_score, trace_id)
     VALUES ($1,$2,$3,$4,'low',1,$5,$6,$7)`,
    [
      episodeId,
      `competence-run-${episodeId}`,
      'competence-test-agent',
      'Competence proof fixture',
      successful ? 'success' : 'partial_success',
      successful ? 1 : 0,
      traceId,
    ]
  );
  await db.query(
    `INSERT INTO trajectory_store
       (id, episode_id, step_index, state_json, action_json, observation_json,
        reward, done, info_json, policy_version, is_successful, is_simulation)
     VALUES ($1,$2,0,$3::jsonb,$4::jsonb,$5::jsonb,$6,true,$7::jsonb,'policy-before',$8,true)`,
    [
      trajectoryId,
      episodeId,
      JSON.stringify({ task: 'competence-proof' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
    ]
  );
  return trajectoryId;
}

async function createSkill(skillKey: string): Promise<{ regressionTestIds: string[] }> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds = [
    await createTrajectory(true, traceId),
    await createTrajectory(false, traceId),
  ];
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: 'competence-proof',
    createdBy: 'competence-proof-test',
    traceId,
  });
  const run = await learner.runLearner({
    learnerType: 'prompt_update',
    replayBatchId: replayBatch.replayBatchId,
    baselinePolicyVersion: 'policy-before',
    traceId,
  });
  const runDetails = await learner.getLearnerRun(run.learnerRunId);
  const candidateId = runDetails.candidates[0].id;
  const regressionCases = await regressionTestGenerator.generateForCandidate(candidateId);
  await skillLibrary.registerSkillVersion({
    skill_key: skillKey,
    version: '1.0.0',
    candidate_id: candidateId,
    contract: { inputs: ['goal'], outputs: ['plan'] },
  });
  return { regressionTestIds: regressionCases.map((row) => row.id) };
}

describe('proof of competence', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('mints idempotent competence proof when every regression result passes threshold', async () => {
    const skillKey = `competence_skill_${Date.now()}`;
    const { regressionTestIds } = await createSkill(skillKey);
    const results = regressionTestIds.map((regressionTestId) => ({
      regression_test_id: regressionTestId,
      passed: true,
      score: 0.93,
      evidence: { evaluator: 'deterministic-regression-harness' },
    }));

    const proof = await proofOfCompetence.mintProof({
      skill_key: skillKey,
      evaluation_label: 'held_out_regression_v1',
      threshold: 0.9,
      results,
    });

    expect(proof.passed).toBe(true);
    expect(Number(proof.aggregate_score)).toBeCloseTo(0.93);
    expect(proof.proof_hash).toMatch(/^[0-9a-f]{64}$/);
    expect(proof.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const duplicate = await proofOfCompetence.mintProof({
      skill_key: skillKey,
      evaluation_label: 'held_out_regression_v1',
      threshold: 0.9,
      results,
    });
    expect(duplicate.id).toBe(proof.id);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [proof.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });

  test('rejects incomplete, failing, or below-threshold evaluations', async () => {
    const skillKey = `competence_reject_${Date.now()}`;
    const { regressionTestIds } = await createSkill(skillKey);
    const passingResults = regressionTestIds.map((regressionTestId) => ({
      regression_test_id: regressionTestId,
      passed: true,
      score: 0.92,
    }));

    await expect(
      proofOfCompetence.mintProof({
        skill_key: skillKey,
        evaluation_label: 'missing_result',
        threshold: 0.8,
        results: passingResults.slice(1),
      })
    ).rejects.toThrow(/missing regression evaluation results/);

    await expect(
      proofOfCompetence.mintProof({
        skill_key: skillKey,
        evaluation_label: 'failed_case',
        threshold: 0.8,
        results: passingResults.map((result, index) => index === 0 ? { ...result, passed: false } : result),
      })
    ).rejects.toThrow(/requires all regression results to pass/);

    await expect(
      proofOfCompetence.mintProof({
        skill_key: skillKey,
        evaluation_label: 'below_threshold',
        threshold: 0.95,
        results: passingResults,
      })
    ).rejects.toThrow(/requires all regression results to pass/);
  });
});
