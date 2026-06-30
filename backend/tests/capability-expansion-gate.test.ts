import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { db } from '../src/db/client';
import { LearnerService } from '../src/services/learner.service';
import { capabilityExpansionGate } from '../src/services/capability-expansion-gate.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { institutionsService } from '../src/services/institutions.service';
import { proofOfCompetence } from '../src/services/proof-of-competence.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';
import { skillLibrary } from '../src/services/skill-library.service';

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
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function insertTrust(subjectId: string, domain: string): Promise<void> {
  await db.query(
    `INSERT INTO trust_scores
       (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
        n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
     VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),12,12,0.08,0.18,0.02,0.88,false)`,
    [subjectId, domain]
  );
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `expansion-proof-${domainKey}-${Date.now()}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `expansion_${domainKey}_${Date.now()}`,
    domain: domainKey,
    purpose: 'Capability expansion gate institution',
    authorityScope: ['domain_onboarding', 'capability_expansion'],
  });
  await insertTrust(proofSubject, domainKey);
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
      `expansion-run-${episodeId}`,
      'expansion-test-agent',
      'Capability expansion fixture',
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
      JSON.stringify({ task: 'capability-expansion' }),
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
    batchLabel: 'capability-expansion',
    createdBy: 'capability-expansion-test',
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
    contract: { inputs: ['domain_context'], outputs: ['domain_action_plan'] },
  });
  await proofOfCompetence.mintProof({
    skill_key: skillKey,
    evaluation_label: 'capability_gate_eval',
    threshold: 0.85,
    results: regressionCases.map((row) => ({
      regression_test_id: row.id,
      passed: true,
      score: 0.91,
    })),
  });
}

describe('capability expansion gate', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('approves expansion only with active domain, current skill proof, and score above baseline', async () => {
    const domainKey = `expansion_domain_${Date.now()}`;
    const skillKey = `expansion_skill_${Date.now()}`;
    await activateDomain(domainKey);
    await createProvenSkill(skillKey);

    const decision = await capabilityExpansionGate.evaluate({
      domain_key: domainKey,
      skill_key: skillKey,
      benchmark_name: 'capability_expansion_gate_smoke',
      evaluation_label: 'capability_gate_eval',
      baseline_score: 0.7,
    });

    expect(decision.decision).toBe('approved');
    expect(decision.domain_key).toBe(domainKey);
    expect(Number(decision.proof_score)).toBeCloseTo(0.91);
    expect(decision.event_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const generality = await db.query(
      `SELECT domains_evaluated, domains_above_baseline, generality_score
         FROM generality_metric_runs
        WHERE id = $1`,
      [decision.generality_run_id]
    );
    expect(generality.rows[0]).toMatchObject({
      domains_evaluated: 1,
      domains_above_baseline: 1,
    });
    expect(Number(generality.rows[0].generality_score)).toBeCloseTo(1);

    const duplicate = await capabilityExpansionGate.evaluate({
      domain_key: domainKey,
      skill_key: skillKey,
      benchmark_name: 'capability_expansion_gate_smoke',
      evaluation_label: 'capability_gate_eval',
      baseline_score: 0.7,
    });
    expect(duplicate.id).toBe(decision.id);

    const outbox = await db.query('SELECT id FROM event_outbox WHERE event_log_id = $1', [decision.event_log_id]);
    expect(outbox.rowCount).toBe(1);
  });

  test('rejects missing domain, missing proof, or proof score below baseline', async () => {
    const skillKey = `expansion_reject_skill_${Date.now()}`;
    await createProvenSkill(skillKey);

    await expect(
      capabilityExpansionGate.evaluate({
        domain_key: `missing_domain_${Date.now()}`,
        skill_key: skillKey,
        benchmark_name: 'capability_expansion_gate_smoke',
        baseline_score: 0.7,
      })
    ).rejects.toThrow(/active domain not found/);

    const domainKey = `expansion_reject_domain_${Date.now()}`;
    await activateDomain(domainKey);
    await expect(
      capabilityExpansionGate.evaluate({
        domain_key: domainKey,
        skill_key: `missing_skill_${Date.now()}`,
        benchmark_name: 'capability_expansion_gate_smoke',
        baseline_score: 0.7,
      })
    ).rejects.toThrow(/active skill not found/);

    await expect(
      capabilityExpansionGate.evaluate({
        domain_key: domainKey,
        skill_key: skillKey,
        benchmark_name: 'capability_expansion_gate_smoke',
        baseline_score: 0.95,
      })
    ).rejects.toThrow(/proof score above baseline/);
  });
});
