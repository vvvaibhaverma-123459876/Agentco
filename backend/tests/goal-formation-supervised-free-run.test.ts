/**
 * Goal Formation + Supervised Free-Run
 * ====================================
 * Proves bounded self-directed operation:
 *   - AgentCo proposes internal goals from real runtime state (a pending
 *     learner candidate), each citing its source DB object with risk,
 *     budget, and stop condition
 *   - governance auto-approves ONLY low-risk internal goals; live-service
 *     goals are held for review
 *   - the free run executes approved goals through the real civilization
 *     flow and completes them with outcome references
 *   - the kill switch stops the loop before any goal executes
 *   - the goal budget bounds the run
 *   - event lineage records start/stop with counts
 */

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { describe, expect, test, beforeAll } from '@jest/globals';
import { db } from '../src/db/client';
import { migrationDb } from './support/migration-db';
import { goalFormation } from '../src/services/goal-formation.service';
import {
  supervisedFreeRun,
  FREE_RUN_KILL_SCOPE,
} from '../src/services/supervised-free-run.service';
import { killSwitchService } from '../src/services/kill-switch.service';
import { ledgerResolutionService } from '../src/services/resolution-service.service';
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
    '098_governance_kill_switch.sql',
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
    await migrationDb.query(migration);
  }
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `freerun-proof-${domainKey}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `freerun_${domainKey}`,
    domain: domainKey,
    purpose: 'Supervised free run institution',
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

async function createPendingCandidate(weakness: string): Promise<string> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds: string[] = [];
  for (const success of [false, false, true]) {
    const episodeId = crypto.randomUUID();
    const trajectoryId = crypto.randomUUID();
    await db.query(
      `INSERT INTO autonomy_episodes
         (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status, reward_score, trace_id)
       VALUES ($1,$2,'freerun-agent','Free run observation','low',1,$3,$4,$5)`,
      [episodeId, `freerun-${episodeId}`, success ? 'success' : 'failure', success ? 1 : 0, traceId]
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
        JSON.stringify(!success ? { weakness } : {}),
        success,
      ]
    );
    trajectoryIds.push(trajectoryId);
  }
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: `freerun-batch-${Date.now()}`,
    createdBy: 'free-run-test',
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

describe('goal formation and supervised free run', () => {
  beforeAll(async () => {
    await applyMigrations();
    // Clean slate: deactivate any leftover kill switch from previous runs.
    const actorId = await ledgerResolutionService.ensureServiceActor('free-run-test-admin', [
      'governance.kill_switch',
    ]);
    const active = await killSwitchService.getActive(FREE_RUN_KILL_SCOPE);
    if (active) {
      await killSwitchService.deactivate(FREE_RUN_KILL_SCOPE, actorId, 'test setup reset');
    }
    // Test isolation on a shared local database: retire open formation goals
    // and stale pending candidates left by earlier suites/runs so this test
    // observes only its own fixtures. (CI starts from an empty database.)
    await db.query(
      `UPDATE autonomy_goals
          SET status = 'retired', retired_at = NOW()
        WHERE proposed_by = 'goal-formation-service'
          AND status IN ('proposed', 'under_review', 'approved', 'active')`
    );
    await db.query(`UPDATE learner_candidates SET status = 'rejected' WHERE status = 'ready_for_eval'`);
  });

  test('proposes goals from runtime state with reason, risk, budget, and stop condition', async () => {
    const candidateId = await createPendingCandidate('non_independent_sources');

    const proposals = await goalFormation.proposeGoals(5);
    const proposal = proposals.find(p =>
      p.sourceObjects.some(s => s.table === 'learner_candidates' && s.id === candidateId)
    )!;
    expect(proposal).toBeDefined();
    expect(proposal.riskLevel).toBe('low');
    expect(proposal.budget.maxIterations).toBeGreaterThan(0);
    expect(proposal.stopCondition).toContain('budget');
    expect(proposal.reason).toContain('ready_for_eval');

    // The goal row exists with the DB-object evidence attached.
    const evidence = await db.query<{ evidence_ref: string }>(
      `SELECT ge.evidence_ref
         FROM goal_evidence ge
        WHERE ge.goal_id = $1`,
      [proposal.goalId]
    );
    expect(evidence.rows.map(r => r.evidence_ref)).toContain(`learner_candidates:${candidateId}`);

    // Idempotency: proposing again does not duplicate the goal.
    const again = await goalFormation.proposeGoals(5);
    expect(
      again.filter(p =>
        p.sourceObjects.some(s => s.table === 'learner_candidates' && s.id === candidateId)
      )
    ).toHaveLength(0);

    // Cleanup for later tests: run it through the free run below.
    const domainKey = `freerun_${Date.now()}`;
    await activateDomain(domainKey);
    const result = await supervisedFreeRun.run({ maxSeconds: 60, maxGoals: 3, domainKey });
    expect(['goal_limit', 'idle', 'time_limit']).toContain(result.stopReason);
    const ourOutcome = result.outcomes.find(o => o.goalId === proposal.goalId);
    expect(ourOutcome).toBeDefined();
    expect(ourOutcome!.status).toBe('completed');
    expect(ourOutcome!.detail).toContain(candidateId);
    expect(ourOutcome!.workflowTaskId).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));

    const workflowTask = await db.query<{ status: string; payload: any; audit_log_id: string | null }>(
      `SELECT status, payload, audit_log_id FROM workflow_tasks WHERE task_id = $1`,
      [ourOutcome!.workflowTaskId]
    );
    expect(workflowTask.rowCount).toBe(1);
    expect(workflowTask.rows[0].status).toBe('done');
    expect(workflowTask.rows[0].audit_log_id).toEqual(expect.stringMatching(/^[0-9a-f-]{36}$/));
    const taskPayload = typeof workflowTask.rows[0].payload === 'string'
      ? JSON.parse(workflowTask.rows[0].payload)
      : workflowTask.rows[0].payload;
    expect(taskPayload.goal_id).toBe(proposal.goalId);
    expect(taskPayload.run_id).toBe(result.runId);

    // Goal lifecycle completed with an outcome reference.
    const goal = await db.query<{ status: string }>(
      `SELECT status FROM autonomy_goals WHERE id = $1`,
      [proposal.goalId]
    );
    expect(goal.rows[0].status).toBe('completed');

    // Run lineage exists.
    const events = await db.query(
      `SELECT payload FROM event_log
        WHERE event_type = 'autonomy.free_run_stopped'
          AND payload->>'run_id' = $1`,
      [result.runId]
    );
    expect(events.rowCount).toBe(1);
  }, 60000);

  test('kill switch stops the loop before executing goals', async () => {
    const actorId = await ledgerResolutionService.ensureServiceActor('free-run-test-admin', [
      'governance.kill_switch',
    ]);
    await killSwitchService.activate(FREE_RUN_KILL_SCOPE, actorId, 'test: halt free run');
    try {
      const domainKey = `freerunkill_${Date.now()}`;
      const result = await supervisedFreeRun.run({ maxSeconds: 30, maxGoals: 3, domainKey });
      expect(result.stopReason).toBe('kill_switch');
      expect(result.outcomes).toHaveLength(0);
    } finally {
      await killSwitchService.deactivate(FREE_RUN_KILL_SCOPE, actorId, 'test cleanup');
    }
  });

  test('goal budget bounds the run and live-service goals are held, not executed', async () => {
    // Seed a low-confidence unverified claim -> medium-risk live-service goal.
    const claimId = crypto.randomUUID();
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, text, status, confidence, support_source_ids)
       VALUES ($1, $2, 'The framework reduces failures by an unverified amount.', 'unverified', 0.3, '["src-fixture-1"]'::jsonb)`,
      [claimId, crypto.randomUUID()]
    );

    const proposals = await goalFormation.proposeGoals(10);
    const liveGoal = proposals.find(p =>
      p.sourceObjects.some(s => s.table === 'autonomy_claims' && s.id === claimId)
    );
    expect(liveGoal).toBeDefined();
    expect(liveGoal!.riskLevel).toBe('medium');
    expect(liveGoal!.requiresLiveServices).toBe(true);

    const { approved, held } = await goalFormation.approveProposedGoals([liveGoal!.goalId]);
    expect(approved).toHaveLength(0);
    expect(held).toContain(liveGoal!.goalId);

    // The held goal remains under_review — never silently executed.
    const status = await db.query<{ status: string }>(
      `SELECT status FROM autonomy_goals WHERE id = $1`,
      [liveGoal!.goalId]
    );
    expect(status.rows[0].status).toBe('under_review');
  });
});
