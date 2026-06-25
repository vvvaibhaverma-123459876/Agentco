import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { institutionWorkAssignmentService } from '../src/services/institution-work-assignment.service';
import { autonomyCivilizationBridgeService } from '../src/services/autonomy-civilization-bridge.service';
describe('Phase 1: Autonomy-Civilization Integration', () => {
  let institutionId: string;
  let departmentIds: { [key: string]: string } = {};
  let workRequestId: string;

  beforeAll(async () => {
    // Ensure database is ready
    try {
      await db.query('SELECT 1');
      console.log('✅ Database connected');
    } catch (e) {
      console.error('❌ Database connection failed:', e);
      throw e;
    }
  });

  afterAll(async () => {
    // Cleanup
    if (workRequestId) {
      try {
        await db.query('DELETE FROM work_cycle_events WHERE work_request_id = $1', [
          workRequestId,
        ]);
        await db.query('DELETE FROM specialist_performance_history WHERE work_request_id = $1', [
          workRequestId,
        ]);
        await db.query('DELETE FROM institution_work_requests WHERE id = $1', [
          workRequestId,
        ]);
      } catch (e) {
        console.warn('Cleanup warning:', e);
      }
    }

    if (institutionId) {
      try {
        const departmentIdValues = Object.values(departmentIds);
        if (departmentIdValues.length > 0) {
          await db.query('DELETE FROM work_cycle_events WHERE work_request_id IN (SELECT id FROM institution_work_requests WHERE department_id = ANY($1::text[]))', [
            departmentIdValues,
          ]);
          await db.query('DELETE FROM specialist_performance_history WHERE work_request_id IN (SELECT id FROM institution_work_requests WHERE department_id = ANY($1::text[]))', [
            departmentIdValues,
          ]);
          await db.query('DELETE FROM institution_work_requests WHERE department_id = ANY($1::text[])', [
            departmentIdValues,
          ]);
        }
        await db.query('DELETE FROM institution_specialist_assignments WHERE institution_id = $1', [
          institutionId,
        ]);
        await db.query('DELETE FROM departments WHERE parent_id = $1', [institutionId]);
        await db.query('DELETE FROM institution_contracts WHERE institution_id = $1', [
          institutionId,
        ]);
        await db.query('DELETE FROM institutions WHERE id = $1', [institutionId]);
      } catch (e) {
        console.warn('Cleanup warning:', e);
      }
    }
  });

  it('creates institution with 5 mandatory departments', async () => {
    institutionId = `phase1_test_inst_${Date.now()}`;
    await db.query(
      `INSERT INTO institutions (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1, $2, 'institution', NULL, 'active', $3, $4, $5, NOW(), NOW())`,
      [
        institutionId,
        `phase1_test_${Date.now()}`,
        'Phase 1 integration institution',
        JSON.stringify(['research_request']),
        JSON.stringify({ verification_required: true }),
      ]
    );

    const deptNames = ['Production', 'Verification', 'Audit', 'Adversarial', 'Improvement'];
    for (const name of deptNames) {
      const departmentId = `phase1_${name.toLowerCase()}_${Date.now()}`;
      await db.query(
        `INSERT INTO departments
           (id, institution_id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
         VALUES ($1, $2, $3, 'department', $2, 'active', $4, '[]', '{}', NOW(), NOW())`,
        [departmentId, institutionId, name, `${name} department`]
      );
      departmentIds[name] = departmentId;
    }

    console.log(`✅ Institution created: ${institutionId}`);
    console.log(`✅ Departments: ${Object.keys(departmentIds).join(', ')}`);
  });

  it('assigns specialists to departments', async () => {
    expect(institutionId).toBeDefined();

    const assignments = [
      { dept: 'Production', role: 'researcher' },
      { dept: 'Production', role: 'data_analyst' },
      { dept: 'Verification', role: 'quality_auditor' },
      { dept: 'Audit', role: 'contradiction_hunter' },
      { dept: 'Adversarial', role: 'sentiment_analyzer' },
      { dept: 'Improvement', role: 'reviewer' },
    ];

    for (const { dept, role } of assignments) {
      const result = await institutionWorkAssignmentService.assignSpecialistToDepartment(
        institutionId,
        departmentIds[dept],
        role,
        0.5  // Initial reputation
      );

      expect(result.id).toBeDefined();
      expect(['created', 'updated']).toContain(result.status);
    }

    console.log(`✅ Assigned ${assignments.length} specialists to departments`);
  });

  it('submits work request from institution', async () => {
    expect(institutionId).toBeDefined();

    const workRequest = await institutionWorkAssignmentService.submitWorkRequest({
      institution_id: institutionId,
      department_id: departmentIds['Production'],
      objective: 'Research AI safety governance frameworks',
      required_specialists: [
        { role: 'researcher', priority: 1 },
        { role: 'data_analyst', priority: 2 },
      ],
      budget: {
        tokens: 50000,
        iterations: 100,
        seconds: 7200,
      },
      verification_required: true,
      reputation_metric: 'evidence_quality',
      risk_level: 'low',
    });

    expect(workRequest.id).toBeDefined();
    expect(workRequest.status).toBe('queued');
    expect(workRequest.institution_id).toBe(institutionId);

    workRequestId = workRequest.id;

    console.log(`✅ Work request created: ${workRequestId}`);
  });

  it('routes work to autonomy system', async () => {
    expect(workRequestId).toBeDefined();

    const autonomyGoalId = await autonomyCivilizationBridgeService.routeWorkToAutonomy(
      workRequestId,
      'Research AI safety governance',
      ['researcher', 'data_analyst']
    );

    expect(autonomyGoalId).toBeDefined();

    // Verify work request updated with goal ID
    const updated = await institutionWorkAssignmentService.getWorkRequest(workRequestId);
    expect(updated?.autonomy_goal_id).toBe(autonomyGoalId);
    expect(updated?.status).toBe('in_progress');

    console.log(`✅ Work routed to autonomy: ${autonomyGoalId}`);
  });

  it('computes specialist performance scores', () => {
    const result = {
      work_request_id: 'test_123',
      specialist_role: 'researcher',
      evidence_count: 8,
      claim_count: 3,
      confidence_avg: 0.85,
      tokens_used: 12000,
      iterations_used: 45,
      time_elapsed_seconds: 300,  // 5 minutes
    };

    const scores = autonomyCivilizationBridgeService.computePerformanceScore(result);

    expect(scores.evidence_quality).toBeGreaterThan(0);
    expect(scores.evidence_quality).toBeLessThanOrEqual(1);
    expect(scores.claim_accuracy).toBe(0.85);  // Should match confidence_avg
    expect(scores.efficiency).toBeGreaterThan(0);
    expect(scores.overall).toBeGreaterThan(0);
    expect(scores.overall).toBeLessThanOrEqual(1);

    // Overall should be weighted average of components
    const expectedOverall = (
      scores.evidence_quality * 0.4 +
      scores.claim_accuracy * 0.35 +
      scores.efficiency * 0.25
    );
    expect(Math.round(scores.overall * 100)).toBe(Math.round(expectedOverall * 100));

    console.log(`✅ Performance scores computed: overall=${scores.overall}`);
  });

  it('reports work completion with reputation update', async () => {
    expect(workRequestId).toBeDefined();

    const completionResult = {
      work_request_id: workRequestId,
      specialist_role: 'researcher',
      evidence_count: 8,
      claim_count: 3,
      confidence_avg: 0.85,
      tokens_used: 12000,
      iterations_used: 45,
      time_elapsed_seconds: 300,
    };

    await autonomyCivilizationBridgeService.reportWorkCompletion(completionResult);

    // Verify work request marked as completed
    const completed = await institutionWorkAssignmentService.getWorkRequest(workRequestId);
    expect(completed?.status).toBe('completed');
    expect(completed?.completed_at).toBeDefined();

    // Verify specialist performance recorded
    const perfResult = await db.query(
      'SELECT * FROM specialist_performance_history WHERE work_request_id = $1',
      [workRequestId]
    );

    expect(perfResult.rows.length).toBeGreaterThan(0);
    const perf = perfResult.rows[0];
    expect(perf.specialist_role).toBe('researcher');
    expect(Number(perf.overall_score)).toBeGreaterThan(0);

    console.log(`✅ Work completion reported with score: ${perf.overall_score}`);
  });

  it('retrieves work request history for institution', async () => {
    expect(institutionId).toBeDefined();

    const requests = await institutionWorkAssignmentService.getInstitutionWorkRequests(
      institutionId
    );

    expect(Array.isArray(requests)).toBe(true);
    expect(requests.length).toBeGreaterThan(0);

    // Verify our work request is in the list
    const ourRequest = requests.find((r) => r.id === workRequestId);
    expect(ourRequest).toBeDefined();
    expect(ourRequest?.status).toBe('completed');

    console.log(`✅ Retrieved ${requests.length} work requests for institution`);
  });

  it('retrieves specialist assignments for department', async () => {
    expect(departmentIds['Production']).toBeDefined();

    const specialists = await institutionWorkAssignmentService.getDepartmentSpecialists(
      departmentIds['Production']
    );

    expect(Array.isArray(specialists)).toBe(true);
    expect(specialists.length).toBeGreaterThan(0);

    // Should have researcher and data_analyst
    const roles = specialists.map((s) => s.specialist_role);
    expect(roles).toContain('researcher');
    expect(roles).toContain('data_analyst');

    console.log(`✅ Retrieved ${specialists.length} specialists for Production department`);
  });

  it('completes full work cycle: request → execute → feedback', async () => {
    expect(institutionId).toBeDefined();

    // Step 1: Submit work request
    const workRequest = await institutionWorkAssignmentService.submitWorkRequest({
      institution_id: institutionId,
      department_id: departmentIds['Verification'],
      objective: 'Verify previous research findings',
      required_specialists: [{ role: 'quality_auditor', priority: 1 }],
      budget: { tokens: 30000, iterations: 50, seconds: 3600 },
      verification_required: false,
      risk_level: 'low',
    });

    expect(workRequest.status).toBe('queued');
    const cycleWorkRequestId = workRequest.id;

    // Step 2: Route to autonomy
    const autonomyGoalId = await autonomyCivilizationBridgeService.routeWorkToAutonomy(
      cycleWorkRequestId,
      'Verify research',
      ['quality_auditor']
    );

    const routed = await institutionWorkAssignmentService.getWorkRequest(cycleWorkRequestId);
    expect(routed?.autonomy_goal_id).toBe(autonomyGoalId);
    expect(routed?.status).toBe('in_progress');

    // Step 3: Report completion
    await autonomyCivilizationBridgeService.reportWorkCompletion({
      work_request_id: cycleWorkRequestId,
      specialist_role: 'quality_auditor',
      evidence_count: 5,
      claim_count: 2,
      confidence_avg: 0.88,
      tokens_used: 8000,
      iterations_used: 30,
      time_elapsed_seconds: 180,
    });

    // Verify cycle complete
    const finalState = await institutionWorkAssignmentService.getWorkRequest(cycleWorkRequestId);
    expect(finalState?.status).toBe('completed');
    expect(finalState?.completed_at).toBeDefined();

    // Cleanup
    await db.query('DELETE FROM work_cycle_events WHERE work_request_id = $1', [
      cycleWorkRequestId,
    ]);
    await db.query('DELETE FROM specialist_performance_history WHERE work_request_id = $1', [
      cycleWorkRequestId,
    ]);
    await db.query('DELETE FROM institution_work_requests WHERE id = $1', [cycleWorkRequestId]);

    console.log(`✅ Full work cycle completed successfully`);
  });
});
