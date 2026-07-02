/**
 * Self-Improvement Closed Loop E2E
 * ================================
 * Proves the full lifecycle with real DB state and event lineage:
 *
 *   observe (trajectories labeled with a failure mode)
 *   -> propose (learner candidate whose strategy derives from the weakness)
 *   -> evaluate (regression cases + measured deterministic benchmark delta)
 *   -> canary (fresh-seed bounded run, must beat baseline)
 *   -> promote (through the real proof/capability/promotion chain)
 *   -> use (skill retrievable by the planner's retrieval path)
 *   -> rollback (failed/regressed skills are retired and stop being used)
 *
 * Everything runs clean-room: no LLM, no network. The benchmark executes the
 * strategy as a decision policy; improvements are measured, not projected.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { LearnerService } from '../src/services/learner.service';
import { candidateEvaluation } from '../src/services/candidate-evaluation.service';
import { skillCanary } from '../src/services/skill-canary.service';
import { skillDeployment } from '../src/services/skill-deployment.service';
import { skillRetrieval } from '../src/services/skill-retrieval.service';
import { deterministicBenchmark } from '../src/services/deterministic-benchmark.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { institutionsService } from '../src/services/institutions.service';

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
    '110_skill_usage_events.sql',
    '111_self_improvement_loop.sql',
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `selfimp-proof-${domainKey}-${Date.now()}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `selfimp_${domainKey}_${Date.now()}`,
    domain: domainKey,
    purpose: 'Self-improvement closed loop institution',
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

/**
 * Observe phase: persist real trajectories. Failures carry a weakness label,
 * which is what the learner mines to propose a strategy.
 */
async function createObservedTrajectory(
  successful: boolean,
  traceId: string,
  weakness?: string
): Promise<string> {
  const episodeId = crypto.randomUUID();
  const trajectoryId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_episodes
       (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status, reward_score, trace_id)
     VALUES ($1,$2,$3,$4,'low',1,$5,$6,$7)`,
    [
      episodeId,
      `selfimp-run-${episodeId}`,
      'selfimp-test-agent',
      'Observed research episode',
      successful ? 'success' : 'failure',
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
      JSON.stringify({ task: 'research-with-sources' }),
      JSON.stringify({ action: successful ? 'select_sources' : 'select_first_sources' }),
      JSON.stringify({ outcome: successful ? 'grounded claim' : 'claim from mirrored sources rejected' }),
      successful ? 1 : 0,
      JSON.stringify(weakness ? { weakness } : {}),
      successful,
    ]
  );
  return trajectoryId;
}

async function createCandidateFromObservations(weakness?: string): Promise<string> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds = [
    await createObservedTrajectory(false, traceId, weakness),
    await createObservedTrajectory(false, traceId, weakness),
    await createObservedTrajectory(true, traceId),
  ];
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: 'self-improvement-loop',
    createdBy: 'self-improvement-e2e',
    traceId,
  });
  const run = await learner.runLearner({
    learnerType: 'heuristic_update',
    replayBatchId: replayBatch.replayBatchId,
    baselinePolicyVersion: 'policy-before',
    traceId,
  });
  const runDetails = await learner.getLearnerRun(run.learnerRunId);
  const candidateId: string = runDetails.candidates[0].id;
  await regressionTestGenerator.generateForCandidate(candidateId);
  await learner.markCandidateReadyForEval(candidateId);
  return candidateId;
}

describe('self-improvement closed loop', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('observe -> propose -> evaluate -> canary -> promote -> use, with event lineage', async () => {
    // 1. Observe: baseline policy measurably underperforms on the benchmark.
    const baselineOnly = deterministicBenchmark.runBenchmark({
      family: 'source_selection',
      strategy: 'baseline',
      iterations: 40,
      seed: 7,
    });
    expect(baselineOnly.strategyScore).toBeLessThan(0.8);

    // 2. Propose: failed trajectories are labeled with the observed weakness;
    //    the learner derives an executable strategy from them.
    const candidateId = await createCandidateFromObservations('non_independent_sources');
    const candidate = await db.query<{ artifact_json: Record<string, unknown> | string; status: string }>(
      `SELECT artifact_json, status FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );
    const rawArtifact = candidate.rows[0].artifact_json;
    const artifact = typeof rawArtifact === 'string' ? JSON.parse(rawArtifact) : rawArtifact;
    expect(artifact.strategy).toBe('prefer_independent_sources');
    expect(artifact.observedWeakness).toBe('non_independent_sources');

    // 3. Evaluate: regression cases plus measured benchmark improvement.
    const evaluation = await candidateEvaluation.evaluateCandidate(candidateId);
    expect(evaluation.passed).toBe(true);
    expect(evaluation.improvementDelta).toBeGreaterThan(0);
    expect(evaluation.caseResults.every(r => r.passed)).toBe(true);

    const statusAfterEval = await db.query<{ status: string }>(
      `SELECT status FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );
    expect(statusAfterEval.rows[0].status).toBe('evaluated');

    // 4. Canary: bounded fresh-seed run must also beat baseline.
    const canary = await skillCanary.runCanary({ candidateId, maxIterations: 20 });
    expect(canary.passed).toBe(true);
    expect(canary.canaryScore).toBeGreaterThan(canary.baselineScore);
    expect(canary.iterationsUsed).toBeLessThanOrEqual(20);

    // 5. Promote through the real chain.
    const domainKey = `selfimp_${Date.now()}`;
    await activateDomain(domainKey);
    const skillKey = `independent_sources_${Date.now()}`;
    const deployed = await skillDeployment.promoteCandidate({
      candidateId,
      skillKey,
      domainKey,
      description:
        'Prefer independent, reliable sources over first-listed sources when gathering evidence.',
    });
    expect(deployed.status).toBe('promoted');

    // 6. Use: the promoted skill is now retrievable by the planner path.
    const skills = await skillRetrieval.retrieveForPlanning({
      goalText: 'Gather evidence from independent reliable sources',
      domain: domainKey,
    });
    expect(skills.map(s => s.skillVersionId)).toContain(deployed.skillVersionId);

    // 7. Lineage: every stage left an event-log record.
    const lineage = await db.query<{ event_type: string }>(
      `SELECT event_type FROM event_log
        WHERE (object_id = $1 AND event_type IN
                ('learner.candidate_evaluation_passed', 'skill.canary_passed'))
           OR (event_type = 'vca.skill_promoted' AND payload->>'skill_key' = $2)
        ORDER BY created_at`,
      [candidateId, skillKey]
    );
    const types = lineage.rows.map(r => r.event_type);
    expect(types).toContain('learner.candidate_evaluation_passed');
    expect(types).toContain('skill.canary_passed');
    expect(types).toContain('vca.skill_promoted');
  }, 30000);

  test('candidates without an executable strategy are rejected, not promoted on projections', async () => {
    const candidateId = await createCandidateFromObservations(undefined);
    const evaluation = await candidateEvaluation.evaluateCandidate(candidateId);
    expect(evaluation.passed).toBe(false);
    expect(evaluation.failureReason).toContain('no executable strategy');

    const status = await db.query<{ status: string }>(
      `SELECT status FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );
    expect(status.rows[0].status).toBe('rejected');

    await expect(skillCanary.runCanary({ candidateId })).rejects.toThrow(/only evaluated candidates/);
  });

  test('rollback retires the skill and removes it from retrieval', async () => {
    const candidateId = await createCandidateFromObservations('ungrounded_snippets');
    const evaluation = await candidateEvaluation.evaluateCandidate(candidateId);
    expect(evaluation.passed).toBe(true);
    const canary = await skillCanary.runCanary({ candidateId, maxIterations: 15 });
    expect(canary.passed).toBe(true);

    const domainKey = `selfimprb_${Date.now()}`;
    await activateDomain(domainKey);
    const skillKey = `grounded_snippets_${Date.now()}`;
    const deployed = await skillDeployment.promoteCandidate({
      candidateId,
      skillKey,
      domainKey,
      description: 'Require support snippets to be true token-subsequences of evidence.',
    });

    const before = await skillRetrieval.retrieveForPlanning({
      goalText: 'Ground claims in token-subsequence evidence snippets',
      domain: domainKey,
    });
    expect(before.map(s => s.skillVersionId)).toContain(deployed.skillVersionId);

    const rollback = await skillDeployment.rollbackCandidate(
      candidateId,
      'regressed in later measured use'
    );
    expect(rollback.skillVersionId).toBe(deployed.skillVersionId);

    const after = await skillRetrieval.retrieveForPlanning({
      goalText: 'Ground claims in token-subsequence evidence snippets',
      domain: domainKey,
    });
    expect(after.map(s => s.skillVersionId)).not.toContain(deployed.skillVersionId);

    const candidateStatus = await db.query<{ status: string }>(
      `SELECT status FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );
    expect(candidateStatus.rows[0].status).toBe('rolled_back');

    const rollbackEvent = await db.query(
      `SELECT id FROM event_log WHERE event_type = 'skill.rolled_back' AND object_id = $1`,
      [candidateId]
    );
    expect(rollbackEvent.rowCount).toBe(1);
  });
});
