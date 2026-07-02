/**
 * Skill Consumption E2E
 * =====================
 * Proves the promoted-skill loop is CLOSED: a skill that clears the full
 * promotion path (learner candidate -> regression tests -> skill library ->
 * proof of competence -> capability expansion -> promotion run) is retrieved
 * by the planner, cited in the decided action, and leaves an auditable
 * usage trail in skill_usage_events + event_log.
 *
 * The LLM is a deterministic local HTTP fixture (test-only, per repo
 * convention). It is deterministic in BOTH branches: it cites a skill id only
 * when the planner prompt actually contains a PROMOTED SKILLS block. So the
 * behavioral difference between run 1 and run 2 is driven purely by the
 * skill's presence in the database, not by fixture trickery.
 */

import crypto from 'crypto';
import fs from 'fs';
import http from 'http';
import path from 'path';
import { describe, expect, test, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { AutonomyActionPlannerService } from '../src/services/autonomy-action-planner.service';
import { skillRetrieval } from '../src/services/skill-retrieval.service';
import { LearnerService } from '../src/services/learner.service';
import { domainRegistry } from '../src/services/domain-registry.service';
import { institutionsService } from '../src/services/institutions.service';
import { proofOfCompetence } from '../src/services/proof-of-competence.service';
import { regressionTestGenerator } from '../src/services/regression-test-generator.service';
import { skillLibrary } from '../src/services/skill-library.service';
import { skillPromotionLoop } from '../src/services/skill-promotion-loop.service';

const FIXTURE_PORT = 18921;

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
  ]) {
    const migration = fs.readFileSync(path.resolve(__dirname, `../src/db/migrations/${name}`), 'utf8');
    await db.query(migration);
  }
}

async function activateDomain(domainKey: string): Promise<void> {
  const proofSubject = `skilluse-proof-${domainKey}-${Date.now()}`;
  const institution = await institutionsService.createCanonicalInstitution({
    name: `skilluse_${domainKey}_${Date.now()}`,
    domain: domainKey,
    purpose: 'Skill consumption e2e institution',
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
       (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status, reward_score, trace_id)
     VALUES ($1,$2,$3,$4,'low',1,$5,$6,$7)`,
    [
      episodeId,
      `skilluse-run-${episodeId}`,
      'skilluse-test-agent',
      'Skill consumption fixture',
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
      JSON.stringify({ task: 'skill-consumption' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
    ]
  );
  return trajectoryId;
}

async function createPromotedSkill(
  skillKey: string,
  domainKey: string,
  contractExtras: Record<string, unknown> = {}
): Promise<{ skillVersionId: string }> {
  const learner = new LearnerService();
  const traceId = crypto.randomUUID();
  const trajectoryIds = [await createTrajectory(true, traceId), await createTrajectory(false, traceId)];
  const replayBatch = await learner.createReplayBatch({
    trajectoryIds,
    batchLabel: 'skill-consumption',
    createdBy: 'skill-consumption-e2e',
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
  const version = await skillLibrary.registerSkillVersion({
    skill_key: skillKey,
    version: '1.0.0',
    candidate_id: candidateId,
    contract: {
      inputs: ['goal'],
      outputs: ['plan'],
      domain: domainKey,
      description:
        'When researching sensor calibration drift, always cross-check at least two independent evidence sources before generating a claim.',
      skill_type: 'planner_prompt_strategy',
      risk_tier: 'low',
      usage_constraints: 'Advisory only; never bypass evidence grounding.',
      expected_benefit: 'Fewer ungrounded claims in calibration research goals.',
      ...contractExtras,
    },
  });
  await proofOfCompetence.mintProof({
    skill_key: skillKey,
    evaluation_label: 'skill_consumption_eval',
    threshold: 0.85,
    results: regressionCases.map(row => ({ regression_test_id: row.id, passed: true, score: 0.92 })),
  });
  await skillPromotionLoop.promote({
    domain_key: domainKey,
    skill_key: skillKey,
    benchmark_name: 'skill_consumption_smoke',
    evaluation_label: 'skill_consumption_eval',
    baseline_score: 0.7,
  });
  return { skillVersionId: version.id };
}

// Unique per-test-run token so re-runs against the same database cannot
// cross-contaminate: the fixture only cites a skill whose prompt line
// contains the current token.
let currentTopicToken = '';

describe('skill consumption closes the promotion loop', () => {
  let fixtureServer: http.Server;
  const savedEnv: Record<string, string | undefined> = {};

  beforeAll(async () => {
    await applyMigrations();

    // Deterministic LLM fixture: cites a skill id ONLY when the incoming
    // planner prompt contains a PROMOTED SKILLS line for the current topic.
    fixtureServer = http.createServer((req, res) => {
      let body = '';
      req.on('data', chunk => (body += chunk));
      req.on('end', () => {
        const request = JSON.parse(body || '{}');
        const userContent: string =
          request.messages?.map((m: { content: string }) => m.content).join('\n') ?? '';
        const skillMatch = currentTopicToken
          ? userContent.match(
              new RegExp(`skill_id=([0-9a-f-]{36})[^\\n]*${currentTopicToken}`)
            )
          : null;
        const decision =
          userContent.includes('PROMOTED SKILLS') && skillMatch
            ? {
                action_type: 'evaluate_progress',
                objective: 'Apply promoted cross-check strategy before claiming',
                args: {},
                reasoning: `Following promoted skill ${skillMatch[1]}: cross-check independent sources first.`,
                used_skill_ids: [skillMatch[1]],
              }
            : {
                action_type: 'evaluate_progress',
                objective: 'Baseline progress evaluation',
                args: {},
                reasoning: 'No promoted skills available; default strategy.',
              };
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ choices: [{ message: { content: JSON.stringify(decision) } }] }));
      });
    });
    await new Promise<void>(resolve => fixtureServer.listen(FIXTURE_PORT, resolve));

    for (const key of ['LLM_BASE_URL', 'LLM_API_KEY', 'OPENAI_API_KEY']) savedEnv[key] = process.env[key];
    process.env.LLM_BASE_URL = `http://127.0.0.1:${FIXTURE_PORT}`;
    process.env.LLM_API_KEY = 'deterministic-test-only';
  });

  afterAll(async () => {
    await new Promise<void>((resolve, reject) =>
      fixtureServer.close(err => (err ? reject(err) : resolve()))
    );
    for (const [key, value] of Object.entries(savedEnv)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  });

  test('planner behavior changes after skill promotion, with persisted usage lineage', async () => {
    const planner = new AutonomyActionPlannerService();
    const domainKey = `skilluse_${Date.now()}`;
    const goalId = crypto.randomUUID();
    currentTopicToken = `driftcase${Date.now()}`;
    const goalText = `Research sensor calibration ${currentTopicToken} and produce grounded claims`;

    // Run 1: no promoted skill exists for this domain -> baseline behavior.
    const baseline = await planner.planNextAction(goalId, {
      goalText,
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: '',
      domain: domainKey,
      previousActions: [],
    });
    expect(baseline.args.used_skill_ids).toBeUndefined();
    expect(baseline.reasoning).toContain('default strategy');

    // Promote a skill through the full real chain.
    await activateDomain(domainKey);
    const skillKey = `calibration_crosscheck_${Date.now()}`;
    const { skillVersionId } = await createPromotedSkill(skillKey, domainKey, {
      description: `When researching sensor calibration ${currentTopicToken}, always cross-check at least two independent evidence sources before generating a claim.`,
    });

    // Run 2: same goal, same planner, same deterministic fixture. The only
    // change is the promoted skill in the database.
    const withSkill = await planner.planNextAction(goalId, {
      goalText,
      claimsGenerated: 0,
      evidenceCount: 0,
      loopDetection: { isLooping: false } as any,
      memoryContext: '',
      domain: domainKey,
      previousActions: [],
    });

    // Behavior differs and the skill is cited, not merely present in prompt.
    expect(withSkill.args.used_skill_ids).toEqual([skillVersionId]);
    expect(withSkill.reasoning).toContain(skillVersionId);
    expect(withSkill.objective).not.toBe(baseline.objective);

    // Usage is persisted with event-log provenance.
    const usage = await db.query<{
      usage: string;
      goal_id: string;
      action_id: string;
      event_log_id: string;
    }>(
      `SELECT usage, goal_id, action_id, event_log_id
         FROM skill_usage_events
        WHERE skill_version_id = $1
        ORDER BY created_at DESC`,
      [skillVersionId]
    );
    expect(usage.rowCount).toBeGreaterThanOrEqual(1);
    expect(usage.rows[0].usage).toBe('used');
    expect(usage.rows[0].goal_id).toBe(goalId);
    expect(usage.rows[0].action_id).toBe(withSkill.actionId);
    expect(usage.rows[0].event_log_id).toMatch(/^[0-9a-f-]{36}$/);

    const events = await db.query(
      `SELECT id FROM event_log WHERE id = $1 AND event_type = 'skill.usage_recorded'`,
      [usage.rows[0].event_log_id]
    );
    expect(events.rowCount).toBe(1);
  });

  test('suspended skills are not retrieved', async () => {
    const domainKey = `skillsusp_${Date.now()}`;
    await activateDomain(domainKey);
    const skillKey = `suspended_skill_${Date.now()}`;
    const { skillVersionId } = await createPromotedSkill(skillKey, domainKey);

    const before = await skillRetrieval.retrieveForPlanning({
      goalText: 'Research sensor calibration drift',
      domain: domainKey,
    });
    expect(before.map(s => s.skillVersionId)).toContain(skillVersionId);

    await db.query(`UPDATE skill_library_entries SET status = 'suspended' WHERE skill_key = $1`, [skillKey]);

    const after = await skillRetrieval.retrieveForPlanning({
      goalText: 'Research sensor calibration drift',
      domain: domainKey,
    });
    expect(after.map(s => s.skillVersionId)).not.toContain(skillVersionId);
  });

  test('skills above the permitted risk tier are rejected with an audit trail', async () => {
    const domainKey = `skillrisk_${Date.now()}`;
    await activateDomain(domainKey);
    const skillKey = `high_risk_skill_${Date.now()}`;
    const { skillVersionId } = await createPromotedSkill(skillKey, domainKey, { risk_tier: 'high' });

    const retrieved = await skillRetrieval.retrieveForPlanning({
      goalText: 'Research sensor calibration drift',
      domain: domainKey,
      maxRiskTier: 'low',
    });
    expect(retrieved.map(s => s.skillVersionId)).not.toContain(skillVersionId);

    const rejection = await db.query<{ usage: string; reason: string }>(
      `SELECT usage, reason FROM skill_usage_events WHERE skill_version_id = $1`,
      [skillVersionId]
    );
    expect(rejection.rowCount).toBeGreaterThanOrEqual(1);
    expect(rejection.rows[0].usage).toBe('rejected');
    expect(rejection.rows[0].reason).toContain('risk tier high exceeds permitted low');

    // The same skill IS retrievable when the run permits high-risk skills.
    const highPermitted = await skillRetrieval.retrieveForPlanning({
      goalText: 'Research sensor calibration drift',
      domain: domainKey,
      maxRiskTier: 'high',
    });
    expect(highPermitted.map(s => s.skillVersionId)).toContain(skillVersionId);
  });
});
