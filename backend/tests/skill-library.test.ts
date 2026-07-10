import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { LearnerService } from '../src/services/learner.service';
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
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await migrationDb.query(migration);
  }
}

async function createTrajectory(successful: boolean, traceId: string, simulation: boolean): Promise<string> {
  const episodeId = crypto.randomUUID();
  const trajectoryId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_episodes
       (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status,
        reward_score, trace_id)
     VALUES ($1,$2,$3,$4,'low',1,$5,$6,$7)`,
    [
      episodeId,
      `skill-library-run-${episodeId}`,
      'skill-library-test-agent',
      'Skill library fixture',
      successful ? 'success' : 'partial_success',
      successful ? 1 : 0,
      traceId,
    ]
  );
  await db.query(
    `INSERT INTO trajectory_store
       (id, episode_id, step_index, state_json, action_json, observation_json,
        reward, done, info_json, policy_version, is_successful, is_simulation)
     VALUES ($1,$2,0,$3::jsonb,$4::jsonb,$5::jsonb,$6,true,$7::jsonb,'policy-before',$8,$9)`,
    [
      trajectoryId,
      episodeId,
      JSON.stringify({ task: 'skill-library' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
      simulation,
    ]
  );
  return trajectoryId;
}

async function createCandidate(simulation: boolean): Promise<string> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds = [
    await createTrajectory(true, traceId, simulation),
    await createTrajectory(false, traceId, simulation),
  ];
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: `skill-library-${simulation ? 'sim' : 'real'}`,
    createdBy: 'skill-library-test',
    traceId,
  });
  const run = await learner.runLearner({
    learnerType: 'prompt_update',
    replayBatchId: replayBatch.replayBatchId,
    baselinePolicyVersion: 'policy-before',
    traceId,
  });
  const runDetails = await learner.getLearnerRun(run.learnerRunId);
  return runDetails.candidates[0].id;
}

describe('skill library', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('registers an idempotent skill version from a covered simulation candidate', async () => {
    const candidateId = await createCandidate(true);
    const regressionCases = await regressionTestGenerator.generateForCandidate(candidateId);
    const skillKey = `planner_heuristic_${Date.now()}`;

    const record = await skillLibrary.registerSkillVersion({
      skill_key: skillKey,
      display_name: 'Planner Heuristic',
      version: '1.0.0',
      candidate_id: candidateId,
      contract: {
        inputs: ['goal', 'context'],
        outputs: ['plan'],
        protected_surfaces: ['production_execution'],
      },
      metrics: { projectedScore: 62 },
    });

    expect(record.skill_key).toBe(skillKey);
    expect(record.version).toBe('1.0.0');
    expect(record.candidate_id).toBe(candidateId);
    expect(record.regression_test_ids.sort()).toEqual(regressionCases.map((row) => row.id).sort());
    expect(record.simulation_trained).toBe(true);
    expect(record.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const current = await skillLibrary.getSkill(skillKey);
    expect(current?.id).toBe(record.id);

    const duplicate = await skillLibrary.registerSkillVersion({
      skill_key: skillKey,
      version: '1.0.0',
      candidate_id: candidateId,
      contract: { inputs: ['ignored'], outputs: ['ignored'] },
    });
    expect(duplicate.id).toBe(record.id);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [record.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });

  test('rejects candidates without regression coverage or simulation training', async () => {
    const uncoveredCandidateId = await createCandidate(true);
    await expect(
      skillLibrary.registerSkillVersion({
        skill_key: `uncovered_skill_${Date.now()}`,
        version: '1.0.0',
        candidate_id: uncoveredCandidateId,
        contract: { inputs: ['goal'], outputs: ['plan'] },
      })
    ).rejects.toThrow(/regression coverage/);

    const realCandidateId = await createCandidate(false);
    await regressionTestGenerator.generateForCandidate(realCandidateId);
    await expect(
      skillLibrary.registerSkillVersion({
        skill_key: `real_skill_${Date.now()}`,
        version: '1.0.0',
        candidate_id: realCandidateId,
        contract: { inputs: ['goal'], outputs: ['plan'] },
      })
    ).rejects.toThrow(/simulation-trained/);
  });
});
