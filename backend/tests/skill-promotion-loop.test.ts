import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { LearnerService } from '../src/services/learner.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { institutionsService } from '../src/services/institutions.service';
import { proofOfCompetence } from '../src/services/proof-of-competence.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';
import { skillLibrary } from '../src/services/skill-library.service';
import { skillPromotionLoop } from '../src/services/skill-promotion-loop.service';

async function applyMigrations() {
  for (const name of [
    '004_decision_log.sql',
    '012_decision_log_chain.sql',
    '014_decision_log_immutability_triggers.sql',
    '009_trust_scores.sql',
    '052b_institutions.sql',
    '062_runtime_schema_compatibility.sql',
    '079_identity_authority.sql',
    '080_event_log.sql',
    '083_transactional_outbox.sql',
    '102_domain_registry.sql',
    '103_generality_metric_tracker.sql',
    '104_candidate_regression_tests.sql',
    '105_skill_library.sql',
    '106_proof_of_competence.sql',
    '107_capability_expansion_gate.sql',
    '108_skill_promotion_loop.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `promotion-proof-${domainKey}-${Date.now()}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `promotion_${domainKey}_${Date.now()}`,
    domain: domainKey,
    purpose: 'Skill promotion loop institution',
    authorityScope: ['domain_onboarding', 'capability_expansion', 'skill_promotion'],
  });
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),12,12,0.08,0.18,0.02,0.9,false)`,
    [proofSubject, domainKey]
  );
  await domainRegistry.registerDomain({
    domain_key: domainKey,
    institution_id: institution.institutionId,
    proof_subject_id: proofSubject,
    required_trust_threshold: 0.7,
  });
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
      `promotion-run-${episodeId}`,
      'promotion-test-agent',
      'Skill promotion fixture',
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
      JSON.stringify({ task: 'skill-promotion' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
    ]
  );
  return trajectoryId;
}

async function createProvenSkill(skillKey: string): Promise<void> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds = [
    await createTrajectory(true, traceId),
    await createTrajectory(false, traceId),
  ];
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: 'skill-promotion',
    createdBy: 'skill-promotion-test',
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
  await proofOfCompetence.mintProof({
    skill_key: skillKey,
    evaluation_label: 'promotion_eval',
    threshold: 0.85,
    results: regressionCases.map((row) => ({
      regression_test_id: row.id,
      passed: true,
      score: 0.92,
    })),
  });
}

describe('skill promotion loop', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('promotes a proven skill through protected-surface and capability gates', async () => {
    const domainKey = `promotion_domain_${Date.now()}`;
    const skillKey = `promotion_skill_${Date.now()}`;
    await activateDomain(domainKey);
    await createProvenSkill(skillKey);

    const run = await skillPromotionLoop.promote({
      domain_key: domainKey,
      skill_key: skillKey,
      benchmark_name: 'skill_promotion_loop_smoke',
      evaluation_label: 'promotion_eval',
      baseline_score: 0.7,
    });

    expect(run.status).toBe('promoted');
    expect(run.protected_surface_result_json).toEqual(expect.objectContaining({
      valid: true,
      touchedSurfaces: [],
    }));
    expect(run.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const duplicate = await skillPromotionLoop.promote({
      domain_key: domainKey,
      skill_key: skillKey,
      benchmark_name: 'skill_promotion_loop_smoke',
      evaluation_label: 'promotion_eval',
      baseline_score: 0.7,
    });
    expect(duplicate.id).toBe(run.id);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [run.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });
});
