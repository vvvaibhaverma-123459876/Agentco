import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { LearnerService } from '../src/services/learner.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';

async function applyMigration(name: string) {
  const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
  await migrationDb.query(migration);
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
      `regression-generator-run-${episodeId}`,
      'regression-generator-test-agent',
      'Regression generator fixture',
      successful ? 'success' : 'partial_success',
      successful ? 1 : 0,
      traceId,
    ]
  );
  await db.query(
    `INSERT INTO trajectory_store
       (id, episode_id, step_index, state_json, action_json, observation_json,
        reward, done, info_json, policy_version, is_successful, is_simulation)
     VALUES ($1,$2,0,$3::jsonb,$4::jsonb,$5::jsonb,$6,true,$7::jsonb,'policy-before', $8, false)`,
    [
      trajectoryId,
      episodeId,
      JSON.stringify({ task: 'regression-generator' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
    ]
  );
  return trajectoryId;
}

describe('regression test generator', () => {
  const learner = new LearnerService();

  beforeAll(async () => {
    await applyMigration('104_candidate_regression_tests.sql');
  });

  test('derives deterministic regression tests from a learner candidate', async () => {
    const traceId = crypto.randomUUID();
    const trajectoryIds = [
      await createTrajectory(true, traceId),
      await createTrajectory(false, traceId),
    ];
    const replayBatch = await learner.createReplayBatch({
      trajectoryIds,
      batchLabel: 'regression-generator-test',
      createdBy: 'regression-generator-test',
      traceId,
    });
    const run = await learner.runLearner({
      learnerType: 'prompt_update',
      replayBatchId: replayBatch.replayBatchId,
      baselinePolicyVersion: 'policy-before',
      traceId,
    });
    const runDetails = await learner.getLearnerRun(run.learnerRunId);
    const candidate = runDetails.candidates[0];

    const generated = await regressionTestGenerator.generateForCandidate(candidate.id);
    expect(generated.map((row) => row.case_name).sort()).toEqual([
      'artifact_hash_stability',
      'preserve_baseline_success_rate',
      'projected_score_not_below_baseline',
      'simulation_training_guard',
    ]);
    expect(generated.every((row) => row.artifact_hash === candidate.artifact_hash)).toBe(true);
    expect(generated.every((row) => row.event_log_id)).toBe(true);

    const metricFloor = generated.find((row) => row.case_name === 'preserve_baseline_success_rate');
    expect(metricFloor?.assertion_json).toEqual(expect.objectContaining({
      metric: 'success_rate',
      operator: '>=',
      threshold: 0.5,
    }));

    const duplicate = await regressionTestGenerator.generateForCandidate(candidate.id);
    expect(duplicate.map((row) => row.id).sort()).toEqual(generated.map((row) => row.id).sort());

    const outbox = await db.query(
      `SELECT COUNT(*)::int AS count
         FROM event_outbox
        WHERE event_log_id = ANY($1::uuid[])`,
      [generated.map((row) => row.event_log_id)]
    );
    expect(outbox.rows[0].count).toBe(4);
  });

  test('rejects missing candidates', async () => {
    await expect(regressionTestGenerator.generateForCandidate(crypto.randomUUID())).rejects.toThrow(/learner candidate not found/);
  });
});
