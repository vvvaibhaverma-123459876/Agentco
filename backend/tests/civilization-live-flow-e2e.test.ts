/**
 * Civilization Live Flow E2E
 * ==========================
 * Proves institutions act on LIVE runtime events, not hand-seeded isolated
 * objects:
 *
 *   1. A real learner candidate becomes ready_for_eval (live runtime event).
 *   2. The live-flow tick picks it up from the event stream.
 *   3. The domain registry routes it (trust-ordered, fail-closed) to the
 *      qualifying institution's Improvement department.
 *   4. The department executes the REAL evaluation + canary services.
 *   5. The decision is persisted on the work request; a passing candidate is
 *      promoted and becomes retrievable by the planner's skill path.
 *   6. A calibration demotion event is reviewed by the Audit department and
 *      is not re-reviewed on the next tick.
 *   7. Routing fails closed when a domain has no qualifying institution.
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { civilizationLiveFlow } from '../src/services/civilization-live-flow.service';
import { calibrationAwareRouting } from '../src/services/calibration-aware-routing.service';
import { skillRetrieval } from '../src/services/skill-retrieval.service';
import { LearnerService } from '../src/services/learner.service';
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

async function activateDomain(domainKey: string): Promise<string> {
  const proofSubject = `civflow-proof-${domainKey}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `civflow_${domainKey}`,
    domain: domainKey,
    purpose: 'Civilization live flow institution',
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
  return institution.institutionId;
}

async function createLiveCandidate(batchLabel: string, weakness?: string): Promise<string> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds: string[] = [];
  for (const success of [false, false, true]) {
    const episodeId = crypto.randomUUID();
    const trajectoryId = crypto.randomUUID();
    await db.query(
      `INSERT INTO autonomy_episodes
         (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status, reward_score, trace_id)
       VALUES ($1,$2,'civflow-agent','Live flow observation','low',1,$3,$4,$5)`,
      [episodeId, `civflow-${episodeId}`, success ? 'success' : 'failure', success ? 1 : 0, traceId]
    );
    await db.query(
      `INSERT INTO trajectory_store
         (id, episode_id, step_index, state_json, action_json, observation_json,
          reward, done, info_json, policy_version, is_successful, is_simulation)
       VALUES ($1,$2,0,'{}','{}','{}',$3,true,$4::jsonb,'policy-before',$5,true)`,
      [
        trajectoryId,
        episodeId,
        success ? 1 : 0,
        JSON.stringify(!success && weakness ? { weakness } : {}),
        success,
      ]
    );
    trajectoryIds.push(trajectoryId);
  }
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel,
    createdBy: 'civilization-live-flow-e2e',
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

describe('civilization live flow', () => {
  beforeAll(async () => {
    await applyMigrations();
  });

  test('institution consumes a live candidate event, decides, and the outcome reaches the planner path', async () => {
    const domainKey = `civflow_${Date.now()}`;
    const batchLabel = `civflow-batch-${Date.now()}`;
    const institutionId = await activateDomain(domainKey);

    // Live runtime event: a candidate becomes ready for evaluation.
    const candidateId = await createLiveCandidate(batchLabel, 'non_independent_sources');

    // The stream sees it without any manual seeding of the flow itself.
    const pending = await civilizationLiveFlow.collectPendingEvents(50, {
      batchLabelPrefix: batchLabel,
    });
    expect(pending.map(e => e.objectId)).toContain(candidateId);

    // One bounded tick: route -> department work -> decide -> promote.
    const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 3, {
      batchLabelPrefix: batchLabel,
    });
    const outcome = outcomes.find(o => o.event.objectId === candidateId)!;
    expect(outcome).toBeDefined();
    expect(outcome.institutionId).toBe(institutionId);
    expect(outcome.decision).toBe('promoted');
    expect(outcome.skillVersionId).toMatch(/^[0-9a-f-]{36}$/);

    // The work request is persisted with the decision summary.
    const workRequest = await db.query<{ status: string; result_summary: any }>(
      `SELECT status, result_summary FROM institution_work_requests WHERE id = $1`,
      [outcome.workRequestId]
    );
    expect(workRequest.rows[0].status).toBe('completed');

    // The department decision affects the planner: the promoted skill is
    // retrievable through the same path the planner uses.
    const skills = await skillRetrieval.retrieveForPlanning({
      goalText: 'Institution vetted strategy for source selection',
      domain: domainKey,
    });
    expect(skills.map(s => s.skillVersionId)).toContain(outcome.skillVersionId);

    // Event lineage is auditable end to end.
    const flowEvents = await db.query(
      `SELECT id FROM event_log
        WHERE event_type = 'civilization.candidate_processed'
          AND payload->>'candidate_id' = $1`,
      [candidateId]
    );
    expect(flowEvents.rowCount).toBe(1);

    // The event is consumed: a second tick has nothing left to do.
    const remaining = await civilizationLiveFlow.collectPendingEvents(50, {
      batchLabelPrefix: batchLabel,
    });
    expect(remaining.map(e => e.objectId)).not.toContain(candidateId);
  }, 30000);

  test('failing candidates are rolled back by the institution, not promoted', async () => {
    const domainKey = `civflowfail_${Date.now()}`;
    const batchLabel = `civflowfail-batch-${Date.now()}`;
    await activateDomain(domainKey);

    // No weakness label -> projection-only candidate -> must be rejected.
    const candidateId = await createLiveCandidate(batchLabel, undefined);
    const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 3, {
      batchLabelPrefix: batchLabel,
    });
    const outcome = outcomes.find(o => o.event.objectId === candidateId)!;
    expect(outcome.decision).toBe('rolled_back');
    expect(outcome.skillVersionId).toBeNull();

    const workRequest = await db.query<{ status: string }>(
      `SELECT status FROM institution_work_requests WHERE id = $1`,
      [outcome.workRequestId]
    );
    expect(workRequest.rows[0].status).toBe('failed');
  });

  test('calibration demotion events are reviewed by the Audit department exactly once', async () => {
    const domainKey = `civflowaudit_${Date.now()}`;
    await activateDomain(domainKey);

    // Produce a real demotion event through the calibration routing service.
    const demotedAgent = `civflow-demoted-${crypto.randomUUID().slice(0, 8)}`;
    await db.query(
      `INSERT INTO trust_scores
         (subject_id, subject_type, domain, claim_type, horizon_class, window_start, window_end,
          n_predictions, n_resolved, brier_mean, log_mean, ece, trust_factor, force_downgrade)
       VALUES ($1,'agent',$2,'general','short',NOW() - INTERVAL '7 days',NOW(),10,10,0.6,0.9,0.3,0.15,true)`,
      [demotedAgent, domainKey]
    );
    await calibrationAwareRouting.rankAgents({ domain: domainKey, candidateAgentIds: [demotedAgent] });

    const outcomes = await civilizationLiveFlow.runLiveFlowTick(domainKey, 50, {
      batchLabelPrefix: `no-candidates-${Date.now()}`,
    });
    const review = outcomes.find(
      o => o.event.eventType === 'calibration_demotion_review' && o.event.detail.agent_id === demotedAgent
    );
    expect(review).toBeDefined();
    expect(review!.decision).toBe('reviewed');

    // Reviewed demotions are not re-reviewed.
    const secondTick = await civilizationLiveFlow.runLiveFlowTick(domainKey, 50, {
      batchLabelPrefix: `no-candidates-${Date.now()}`,
    });
    expect(
      secondTick.find(
        o => o.event.eventType === 'calibration_demotion_review' && o.event.detail.agent_id === demotedAgent
      )
    ).toBeUndefined();
  });

  test('routing fails closed for domains without a qualifying institution', async () => {
    await expect(
      civilizationLiveFlow.runLiveFlowTick(`nonexistent_domain_${Date.now()}`, 1, {
        batchLabelPrefix: `none-${Date.now()}`,
      })
    ).resolves.toEqual([]); // no events -> no work; now force an event through:

    const batchLabel = `civflownodomain-${Date.now()}`;
    await createLiveCandidate(batchLabel, 'non_independent_sources');
    await expect(
      civilizationLiveFlow.runLiveFlowTick(`nonexistent_domain_${Date.now()}`, 1, {
        batchLabelPrefix: batchLabel,
      })
    ).rejects.toThrow(/no qualifying institution/);
  });
});
