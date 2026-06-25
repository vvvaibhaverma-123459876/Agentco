/**
 * Civilization Free-Run — real assertions against the vision's Definition of Done.
 * Gated RUN_LIVE_SMOKE=1 (needs Postgres). Fixture mode => no LLM/web, deterministic.
 *
 * Covers DoD: runs without a user goal (#2,3), routes to a society agenda (#4), executes a
 * bounded task producing a claim (#5,6), promotes a grounded claim through the gate (#7),
 * BLOCKS an unverified claim (#8), registers a prediction (#9), writes a report artifact (#11).
 */
import { describe, it, expect, afterAll } from '@jest/globals';
import fs from 'fs';
import path from 'path';
import { v4 as uuid } from 'uuid';
import { CivilizationFreeRunService } from '../../src/services/civilization-free-run.service';
import { db } from '../../src/db/client';
import { overrideQueue } from '../../src/services/override-queue.service';

const RUN = process.env.RUN_LIVE_SMOKE === '1';
const d = RUN ? describe : describe.skip;

d('civilization free-run (fixture, real Postgres)', () => {
  const svc = new CivilizationFreeRunService();

  afterAll(async () => { await db.end(); });

  it('runs WITHOUT a user goal and completes the full vision loop', async () => {
    const report = await svc.run('fixture');

    // #2/#3 internal goal generated from self-assessment, no user prompt.
    expect(report.weaknesses.length).toBeGreaterThan(0);
    expect(report.internalGoalId).toBeTruthy();
    const goal = await db.query(`SELECT source, proposed_by FROM autonomy_goals WHERE id = $1`, [report.internalGoalId]);
    expect(goal.rows[0].proposed_by).toBe('civilization_free_run');
    expect(goal.rows[0].source).toBe('perception_derived'); // internally derived, not user

    // #4 routed to a society agenda (persisted).
    expect(report.agendaItemId).toBeTruthy();
    expect(report.societyId).toMatch(/society/);
    expect(report.institutionId).toBeTruthy();
    expect(report.taskType).toMatch(/promote_supported_claims|ingest_research_evidence/);
    const agenda = await db.query(`SELECT content FROM autonomy_memory WHERE id = $1`, [report.agendaItemId]);
    expect(agenda.rows[0].content.societyId).toBe(report.societyId);
    expect(agenda.rows[0].content.institutionId).toBe(report.institutionId);
    expect(agenda.rows[0].content.taskType).toBe(report.taskType);

    // #5/#6/#7 bounded task produced a claim and the gate PROMOTED the grounded one.
    expect(report.claimsProcessed).toBe(1);
    expect(report.claimsPromoted).toBe(1);
    expect(report.claimsBlocked).toBe(0);
    expect(report.contradictionChecks).toBe(1);
    expect(report.contradictionsDetected).toBe(0);
    expect(report.agentSpawnProposals).toBeGreaterThanOrEqual(1);
    expect(report.selfImprovementProposals).toBe(1);
    expect(report.governanceQueueRequests).toBe(report.agentSpawnProposals + report.selfImprovementProposals);
    const action = await db.query(
      `SELECT objective FROM autonomy_goal_actions WHERE goal_id = $1 ORDER BY created_at DESC LIMIT 1`,
      [report.internalGoalId]
    );
    expect(action.rows[0].objective).toContain(report.societyId);
    expect(action.rows[0].objective).toContain(report.institutionId);

    // #9 a prediction was registered for the promoted (now-trusted) claim.
    expect(report.predictionsRegistered).toBe(1);

    // #11 report artifact written.
    const md = path.join(report.reportDir, 'civilization_report.md');
    expect(fs.existsSync(md)).toBe(true);
    expect(fs.readFileSync(md, 'utf8')).toMatch(/Civilization Free-Run Report/);
    const claimsJsonl = path.join(report.reportDir, 'claims.jsonl');
    expect(fs.existsSync(claimsJsonl)).toBe(true);
    expect(fs.readFileSync(claimsJsonl, 'utf8')).toMatch(/claim_id/);
    const eventsJsonl = path.join(report.reportDir, 'events.jsonl');
    expect(fs.existsSync(eventsJsonl)).toBe(true);
    expect(fs.readFileSync(eventsJsonl, 'utf8')).toMatch(/society_agenda/);
    expect(fs.readFileSync(eventsJsonl, 'utf8')).toMatch(/contradiction_detection/);
    const contradictionsJsonl = path.join(report.reportDir, 'contradictions.jsonl');
    expect(fs.existsSync(contradictionsJsonl)).toBe(true);
    const proposalsJsonl = path.join(report.reportDir, 'agent_spawn_proposals.jsonl');
    expect(fs.existsSync(proposalsJsonl)).toBe(true);
    expect(fs.readFileSync(proposalsJsonl, 'utf8')).toMatch(/agent_spawn_proposal|claim_validator|researcher/);
    const selfImprovementJsonl = path.join(report.reportDir, 'self_improvement_proposals.jsonl');
    expect(fs.existsSync(selfImprovementJsonl)).toBe(true);
    expect(fs.readFileSync(selfImprovementJsonl, 'utf8')).toMatch(/self_assessment|review_required/);
    const governanceQueueJsonl = path.join(report.reportDir, 'governance_queue_requests.jsonl');
    expect(fs.existsSync(governanceQueueJsonl)).toBe(true);
    expect(fs.readFileSync(governanceQueueJsonl, 'utf8')).toMatch(/agent_spawn_proposal|self_improvement_proposal/);
  }, 30000);

  it('uses the society agenda to drive the fixture bounded task route', async () => {
    const calibrationWeakness = {
      kind: 'unpromoted_knowledge',
      detail: 'supported claims need promotion',
      recommendedGoal: {
        title: 'Promote supported claims',
        description: 'Run the promotion gate.',
        domain: 'calibration',
      },
    };
    const researchWeakness = {
      kind: 'thin_evidence',
      detail: 'knowledge base has too few claims',
      recommendedGoal: {
        title: 'Gather research evidence',
        description: 'Ingest grounded research.',
        domain: 'research',
      },
    };

    const calibrationGoalId = await svc.generateInternalGoal(calibrationWeakness);
    const researchGoalId = await svc.generateInternalGoal(researchWeakness);
    const calibrationAgenda = await svc.createAgendaItem(calibrationGoalId, calibrationWeakness);
    const researchAgenda = await svc.createAgendaItem(researchGoalId, researchWeakness);

    expect(calibrationAgenda.societyId).toBe('calibration_society');
    expect(calibrationAgenda.institutionId).toBe('evidence_promotion_institution');
    expect(calibrationAgenda.taskType).toBe('promote_supported_claims');
    expect(researchAgenda.societyId).toBe('scientific_society');
    expect(researchAgenda.institutionId).toBe('research_ingestion_institution');
    expect(researchAgenda.taskType).toBe('ingest_research_evidence');

    const [calibrationClaimId] = await svc.executeBoundedTaskFixture(calibrationGoalId, calibrationAgenda);
    const [researchClaimId] = await svc.executeBoundedTaskFixture(researchGoalId, researchAgenda);

    const rows = await db.query(
      `SELECT g.goal_id, g.objective, c.claim_id, c.text
         FROM autonomy_goal_actions g
         JOIN autonomy_claims c ON c.action_id = g.action_id
        WHERE c.claim_id = ANY($1)
        ORDER BY c.generated_at ASC`,
      [[calibrationClaimId, researchClaimId]]
    );
    const byClaim = new Map(rows.rows.map((r: { claim_id: string; objective: string; text: string }) => [r.claim_id, r]));
    expect(byClaim.get(calibrationClaimId)!.objective).toContain('calibration_society/evidence_promotion_institution');
    expect(byClaim.get(calibrationClaimId)!.text).toContain('Calibration improves');
    expect(byClaim.get(researchClaimId)!.objective).toContain('scientific_society/research_ingestion_institution');
    expect(byClaim.get(researchClaimId)!.text).toContain('Bounded gaps between primes');
  }, 20000);

  it('self-assesses contradictions, stale predictions, and weak domains from real Postgres state', async () => {
    const weakDomainGoalId = await svc.generateInternalGoal({
      kind: 'weak-domain-seed',
      detail: 'seed weak domain',
      recommendedGoal: {
        title: 'Seed transfer domain',
        description: 'Create a weak-domain test goal.',
        domain: 'transfer_test_domain',
      },
    });
    const priorSourceId = uuid(), priorActionId = uuid(), priorClaimId = uuid();
    const newSourceId = uuid(), newActionId = uuid(), newClaimId = uuid();
    const weakSourceIds = [uuid(), uuid()];
    const weakActionIds = [uuid(), uuid()];
    const weakClaimIds = [uuid(), uuid()];
    const predictionId = `pred_health_${Date.now()}_${uuid().slice(0, 8)}`;

    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim','health prior contradiction'),
              ($4,$5,$6,'generate_claim','health incoming contradiction'),
              ($7,$8,$9,'generate_claim','health weak domain one'),
              ($10,$11,$12,'generate_claim','health weak domain two')`,
      [
        uuid(), priorActionId, uuid(),
        uuid(), newActionId, uuid(),
        uuid(), weakActionIds[0], weakDomainGoalId,
        uuid(), weakActionIds[1], weakDomainGoalId,
      ]
    );
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,'Prior',$5,NOW(),$6,'web',true,NOW()),
              ($7,$8,$9,$10,'New',$11,NOW(),$12,'web',true,NOW()),
              ($13,$14,$15,$16,'Weak one',$17,NOW(),$18,'web',true,NOW()),
              ($19,$20,$21,$22,'Weak two',$23,NOW(),$24,'web',true,NOW())`,
      [
        uuid(), priorSourceId, priorActionId, 'https://example.org/health-prior', 'Health module claims conflict.', `h-${priorClaimId}`,
        uuid(), newSourceId, newActionId, 'https://example.org/health-new', 'Health module claims conflict.', `h-${newClaimId}`,
        uuid(), weakSourceIds[0], weakActionIds[0], 'https://example.org/weak-one', 'Transfer weak domain claim one.', `h-${weakClaimIds[0]}`,
        uuid(), weakSourceIds[1], weakActionIds[1], 'https://example.org/weak-two', 'Transfer weak domain claim two.', `h-${weakClaimIds[1]}`,
      ]
    );
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7),
              ($8,$9,$10,$11,'supported',0.7,$12,$13,$14),
              ($15,$16,$17,$18,'supported',0.7,$19,$20,$21),
              ($22,$23,$24,$25,'supported',0.7,$26,$27,$28)`,
      [
        uuid(), priorClaimId, priorActionId, 'Health module claims conflict.',
        JSON.stringify([priorSourceId]), JSON.stringify(['Health module claims conflict']), JSON.stringify([priorActionId]),
        uuid(), newClaimId, newActionId, 'Health module claims do not conflict.',
        JSON.stringify([newSourceId]), JSON.stringify(['Health module claims do not conflict']), JSON.stringify([newActionId]),
        uuid(), weakClaimIds[0], weakActionIds[0], 'Transfer weak domain claim one.',
        JSON.stringify([weakSourceIds[0]]), JSON.stringify(['Transfer weak domain claim one']), JSON.stringify([weakActionIds[0]]),
        uuid(), weakClaimIds[1], weakActionIds[1], 'Transfer weak domain claim two.',
        JSON.stringify([weakSourceIds[1]]), JSON.stringify(['Transfer weak domain claim two']), JSON.stringify([weakActionIds[1]]),
      ]
    );
    await db.query(
      `INSERT INTO predictions (prediction_id, category, description, confidence, expected_resolution_by, hypothesis, created_by)
       VALUES ($1, 'civilization_free_run', 'health snapshot stale prediction seed', 0.70, NOW() - INTERVAL '1 day', 'health-test', 'civilization_free_run_test')`,
      [predictionId]
    );

    await svc.detectContradictions([newClaimId]);
    const snapshot = await svc.getHealthSnapshot();
    expect(snapshot.unresolvedContradictions).toBeGreaterThanOrEqual(1);
    expect(snapshot.stalePredictions).toBeGreaterThanOrEqual(1);
    expect(snapshot.weakDomains.some(d => d.domain === 'transfer_test_domain')).toBe(true);

    const weaknesses = await svc.selfAssess();
    expect(weaknesses.map(w => w.kind)).toEqual(expect.arrayContaining([
      'unresolved_contradictions',
      'stale_predictions',
      'weak_domain',
    ]));
    const weakDomain = weaknesses.find(w => w.kind === 'weak_domain' && w.detail.includes('transfer_test_domain'));
    expect(weakDomain?.recommendedGoal.domain).toBe('transfer_test_domain');

    await db.query(`DELETE FROM prediction_resolutions WHERE prediction_id = $1`, [predictionId]);
    await db.query(`DELETE FROM predictions WHERE prediction_id = $1`, [predictionId]);
    await db.query(`DELETE FROM autonomy_goal_actions WHERE action_id = ANY($1)`, [[priorActionId, newActionId, ...weakActionIds]]);
  }, 20000);

  it('#8 BLOCKS an unverified claim (snippet not traceable to its cited source)', async () => {
    // Set up a claim whose support snippet is NOT in its evidence => promotion must block it.
    const sourceId = uuid(), actionId = uuid(), claimId = uuid();
    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim','free-run negative test')`, [uuid(), actionId, uuid()]);
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,'web',true,NOW())`,
      [uuid(), sourceId, actionId, 'https://example.com/x', 'X', 'This abstract is about photosynthesis in plants.', 'h']);
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7)`,
      [uuid(), claimId, actionId, 'The Riemann hypothesis was proven using prime sieves.',
       JSON.stringify([sourceId]), JSON.stringify(['prime sieves prove the Riemann hypothesis']), JSON.stringify([actionId])]);

    const gate = await svc.promotionGate([claimId]);
    expect(gate.blocked).toContain(claimId);
    expect(gate.promoted).not.toContain(claimId);

    const row = await db.query(`SELECT status FROM autonomy_claims WHERE claim_id = $1`, [claimId]);
    expect(row.rows[0].status).toBe('supported'); // NOT promoted

    await db.query(`DELETE FROM autonomy_goal_actions WHERE action_id = $1`, [actionId]);
  }, 20000);

  it('actively detects direct contradictions before promotion and blocks the new claim', async () => {
    const priorSourceId = uuid(), priorActionId = uuid(), priorClaimId = uuid();
    const newSourceId = uuid(), newActionId = uuid(), newClaimId = uuid();
    const proposition = 'Module two widgets converge under calibration';

    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim','free-run contradiction prior')`,
      [uuid(), priorActionId, uuid()]
    );
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,'web',true,NOW())`,
      [uuid(), priorSourceId, priorActionId, 'https://example.org/prior-contradiction', 'Prior', proposition, `h-${priorClaimId}`]
    );
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7)`,
      [uuid(), priorClaimId, priorActionId, proposition,
       JSON.stringify([priorSourceId]), JSON.stringify([proposition]), JSON.stringify([priorActionId])]
    );

    await db.query(
      `INSERT INTO autonomy_goal_actions (id, action_id, goal_id, action_type, objective)
       VALUES ($1,$2,$3,'generate_claim','free-run contradiction incoming')`,
      [uuid(), newActionId, uuid()]
    );
    await db.query(
      `INSERT INTO autonomy_evidence (id, source_id, action_id, url, title, snippet, retrieved_at, content_hash, source_type, is_public_access, created_at)
       VALUES ($1,$2,$3,$4,$5,$6,NOW(),$7,'web',true,NOW())`,
      [uuid(), newSourceId, newActionId, 'https://example.org/new-contradiction', 'New', `${proposition} is disputed.`, `h-${newClaimId}`]
    );
    await db.query(
      `INSERT INTO autonomy_claims (id, claim_id, action_id, text, status, confidence, support_source_ids, support_snippets, derived_from_action_ids)
       VALUES ($1,$2,$3,$4,'supported',0.7,$5,$6,$7)`,
      [uuid(), newClaimId, newActionId, 'Module two widgets do not converge under calibration.',
       JSON.stringify([newSourceId]), JSON.stringify(['Module two widgets do not converge under calibration']), JSON.stringify([newActionId])]
    );

    const findings = await svc.detectContradictions([newClaimId]);
    expect(findings).toHaveLength(1);
    expect(findings[0].claimId).toBe(newClaimId);
    expect(findings[0].contradictingClaimId).toBe(priorClaimId);

    const linked = await db.query(
      `SELECT claim_id, status, contradicted_by, contradicts
         FROM autonomy_claims
        WHERE claim_id = ANY($1)`,
      [[newClaimId, priorClaimId]]
    );
    const byClaim = new Map(linked.rows.map((r: { claim_id: string; status: string; contradicted_by: string[]; contradicts: string[] }) => [r.claim_id, r]));
    expect(byClaim.get(newClaimId)!.status).toBe('contradicted');
    expect(byClaim.get(newClaimId)!.contradicted_by).toContain(priorClaimId);
    expect(byClaim.get(priorClaimId)!.contradicts).toContain(newClaimId);

    const gate = await svc.promotionGate([newClaimId]);
    expect(gate.blocked).toContain(newClaimId);
    expect(gate.promoted).not.toContain(newClaimId);

    await db.query(`DELETE FROM autonomy_goal_actions WHERE action_id = ANY($1)`, [[priorActionId, newActionId]]);
  }, 20000);

  it('creates governance-bound agent spawn proposals without activating specialists', async () => {
    const weakness = {
      kind: 'unpromoted_knowledge',
      detail: 'supported claims need promotion and contradiction review',
      recommendedGoal: {
        title: 'Promote and review supported claims',
        description: 'Run promotion with specialist proposals.',
        domain: 'calibration',
      },
    };
    const goalId = await svc.generateInternalGoal(weakness);
    const agenda = await svc.createAgendaItem(goalId, weakness);
    const before = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );

    const proposals = await svc.proposeAgentSpawns(goalId, agenda, [{
      claimId: 'claim-a',
      contradictingClaimId: 'claim-b',
      reason: 'test contradiction',
    }]);

    expect(proposals.map(p => p.role).sort()).toEqual(['claim_validator', 'contradiction_hunter']);
    for (const proposal of proposals) {
      expect(proposal.governanceStatus).toBe('review_required');
      expect(proposal.constraints.activationRequiresGovernance).toBe(true);
      expect(proposal.constraints.maxDepth).toBe(2);
      expect(proposal.constraints.maxParallelWorkers).toBe(3);
      expect(proposal.budget.tokens).toBeGreaterThan(0);
      expect(proposal.budget.iterations).toBeGreaterThan(0);
      expect(proposal.budget.seconds).toBeGreaterThan(0);
    }

    const memory = await db.query(
      `SELECT content FROM autonomy_memory WHERE id = ANY($1) ORDER BY created_at ASC`,
      [proposals.map(p => p.proposalId)]
    );
    expect(memory.rows).toHaveLength(2);
    expect(memory.rows.every((r: { content: { type: string; governanceStatus: string } }) =>
      r.content.type === 'agent_spawn_proposal' && r.content.governanceStatus === 'review_required'
    )).toBe(true);

    const after = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );
    expect(Number(after.rows[0].n)).toBe(Number(before.rows[0].n));
  }, 20000);

  it('creates governed self-improvement proposals without generating deployable candidates', async () => {
    const weakness = {
      kind: 'thin_evidence',
      detail: 'only fixture-level self-assessment signals are available',
      recommendedGoal: {
        title: 'Improve free-run self-assessment',
        description: 'Deepen self-assessment signals.',
        domain: 'research',
      },
    };
    const goalId = await svc.generateInternalGoal(weakness);
    const beforeMemory = await db.query(
      `SELECT count(*) AS n FROM autonomy_memory WHERE content->>'type' = 'self_improvement_proposal'`
    );

    const proposals = await svc.proposeSelfImprovements(goalId, [weakness], {
      contradictionsDetected: 0,
      agentSpawnProposals: 1,
      errors: [],
    });

    expect(proposals).toHaveLength(1);
    const proposal = proposals[0];
    expect(proposal.governanceStatus).toBe('review_required');
    expect(proposal.targetComponent).toBe('civilization_free_run.self_assessment');
    expect(proposal.affectedFiles).toContain('backend/src/services/civilization-free-run.service.ts');
    expect(proposal.testsToPass).toContain('npx tsc --noEmit');
    expect(proposal.rollbackPlan).toMatch(/Revert/);
    expect(proposal.protectedSurfaceCheck.requiresHumanApproval).toBe(true);
    expect(proposal.protectedSurfaceCheck.attempts.length).toBeGreaterThan(0);
    expect(proposal.expectedImprovement).toMatch(/health-snapshot prioritization|cross-run trends|severity thresholds/);

    const memory = await db.query(
      `SELECT content FROM autonomy_memory WHERE id = $1`,
      [proposal.proposalId]
    );
    expect(memory.rows).toHaveLength(1);
    expect(memory.rows[0].content.type).toBe('self_improvement_proposal');
    expect(memory.rows[0].content.governanceStatus).toBe('review_required');

    const afterMemory = await db.query(
      `SELECT count(*) AS n FROM autonomy_memory WHERE content->>'type' = 'self_improvement_proposal'`
    );
    expect(Number(afterMemory.rows[0].n)).toBe(Number(beforeMemory.rows[0].n) + 1);
  }, 20000);

  it('queues free-run proposals for human governance without approving or executing them', async () => {
    const weakness = {
      kind: 'unpromoted_knowledge',
      detail: 'supported claims need governed review',
      recommendedGoal: {
        title: 'Govern proposal review',
        description: 'Submit proposal outputs to the human override queue.',
        domain: 'calibration',
      },
    };
    const goalId = await svc.generateInternalGoal(weakness);
    const agenda = await svc.createAgendaItem(goalId, weakness);
    const activationsBefore = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );
    const agentProposals = await svc.proposeAgentSpawns(goalId, agenda, []);
    const selfImprovementProposals = await svc.proposeSelfImprovements(goalId, [weakness], {
      contradictionsDetected: 0,
      agentSpawnProposals: agentProposals.length,
      errors: [],
    });

    const requests = await svc.enqueueGovernanceReviewRequests(goalId, agentProposals, selfImprovementProposals);

    expect(requests).toHaveLength(agentProposals.length + selfImprovementProposals.length);
    expect(requests.length).toBeGreaterThanOrEqual(2);
    expect(requests.every(r => r.status === 'pending')).toBe(true);
    expect(requests.map(r => r.proposalType).sort()).toEqual(expect.arrayContaining([
      'agent_spawn_proposal',
      'self_improvement_proposal',
    ]));

    const queueRows = await db.query(
      `SELECT request_id, agent_id, action, status, approval_token, context
         FROM override_queue
        WHERE request_id = ANY($1)
        ORDER BY created_at ASC`,
      [requests.map(r => r.requestId)]
    );
    expect(queueRows.rows).toHaveLength(requests.length);
    for (const row of queueRows.rows) {
      expect(row.agent_id).toBe('civilization_free_run');
      expect(row.status).toBe('pending');
      expect(row.approval_token).toBeNull();
      expect(row.context.goal_id).toBe(goalId);
      expect(row.context.blocked_until_approved).toBe(true);
      expect(['agent_upgrade', 'config_change']).toContain(row.action);
    }

    const activationsAfter = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );
    expect(Number(activationsAfter.rows[0].n)).toBe(Number(activationsBefore.rows[0].n));
  }, 20000);

  it('consumes approval tokens only through a promotion-eligible eval preflight and does not execute', async () => {
    const weakness = {
      kind: 'unpromoted_knowledge',
      detail: 'approval preflight test',
      recommendedGoal: {
        title: 'Approval preflight',
        description: 'Check approved governance requests against eval gates.',
        domain: 'calibration',
      },
    };
    const goalId = await svc.generateInternalGoal(weakness);
    const agenda = await svc.createAgendaItem(goalId, weakness);
    const [proposal] = await svc.proposeAgentSpawns(goalId, agenda, []);
    const [queued] = await svc.enqueueGovernanceReviewRequests(goalId, [proposal], []);
    const activationsBefore = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );

    const pending = await svc.assessGovernanceApprovalReadiness({
      requestId: queued.requestId,
    });
    expect(pending.status).toBe('blocked');
    expect(pending.blockedReason).toMatch(/not approved/);

    const approved = await overrideQueue.resolve(queued.requestId, 'approved', 'human-governor-test', 'preflight test');
    const noEval = await svc.assessGovernanceApprovalReadiness({
      requestId: queued.requestId,
      approvalToken: approved.approval_token,
    });
    expect(noEval.status).toBe('blocked');
    expect(noEval.blockedReason).toMatch(/eval scorecard is required/);

    const failedEvalRunId = await seedFreeRunEvalScorecard(false);
    const failedEval = await svc.assessGovernanceApprovalReadiness({
      requestId: queued.requestId,
      approvalToken: approved.approval_token,
      evalRunId: failedEvalRunId,
    });
    expect(failedEval.status).toBe('blocked');
    expect(failedEval.blockedReason).toMatch(/not promotion eligible/);
    expect(failedEval.scorecard?.promotionEligible).toBe(false);

    const passedEvalRunId = await seedFreeRunEvalScorecard(true);
    const ready = await svc.assessGovernanceApprovalReadiness({
      requestId: queued.requestId,
      approvalToken: approved.approval_token,
      evalRunId: passedEvalRunId,
    });
    expect(ready.status).toBe('ready');
    expect(ready.blockedReason).toBeUndefined();
    expect(ready.scorecard?.promotionEligible).toBe(true);
    expect(ready.proposalType).toBe('agent_spawn_proposal');

    const memory = await db.query(
      `SELECT content
         FROM autonomy_memory
        WHERE content->>'type' = 'governance_approval_preflight'
          AND content->>'requestId' = $1
        ORDER BY created_at DESC`,
      [queued.requestId]
    );
    expect(memory.rows.length).toBeGreaterThanOrEqual(4);
    expect(memory.rows[0].content.status).toBe('ready');

    const activationsAfter = await db.query(
      `SELECT count(*) AS n FROM autonomy_team_activations WHERE parent_goal_id = $1`,
      [goalId]
    );
    expect(Number(activationsAfter.rows[0].n)).toBe(Number(activationsBefore.rows[0].n));
  }, 20000);
});

async function seedFreeRunEvalScorecard(promotionEligible: boolean): Promise<string> {
  const suiteId = uuid();
  const evalRunId = uuid();
  await db.query(
    `INSERT INTO eval_suites (id, name, domain, version, active)
     VALUES ($1, $2, 'civilization_free_run', 1, TRUE)`,
    [suiteId, `civilization-free-run-preflight-${uuid()}`]
  );
  await db.query(
    `INSERT INTO eval_runs (id, suite_id, run_timestamp, status)
     VALUES ($1, $2, NOW(), 'completed')`,
    [evalRunId, suiteId]
  );
  const passScore = promotionEligible ? 1.0 : 0.4;
  await db.query(
    `INSERT INTO eval_scorecards (
       id, eval_run_id, autonomy_score, safety_score, calibration_score, planning_score,
       memory_score, tool_score, reward_score, regression_score, promotion_eligible
     ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
    [
      uuid(),
      evalRunId,
      passScore,
      promotionEligible ? 1.0 : 0.5,
      passScore,
      passScore,
      passScore,
      passScore,
      passScore,
      passScore,
      promotionEligible,
    ]
  );
  return evalRunId;
}
