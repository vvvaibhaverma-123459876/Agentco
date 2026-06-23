import { describe, it, expect, beforeAll, afterAll } from '@jest/globals';
import { db } from '../src/db/client';
import { goalHierarchyService } from '../src/services/goal-hierarchy.service';

describe('Phase 2: Long-Term Coordination - Goal Hierarchies', () => {
  let institutionId: string;
  let rootGoalId: string;
  let subGoal1Id: string;
  let subGoal2Id: string;
  let taskGoals: string[] = [];

  beforeAll(async () => {
    // Setup: Create test institution
    const instResult = await db.query(
      `INSERT INTO institutions (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id`,
      [
        'phase2_test_inst_' + Date.now(),
        `phase2_test_${Date.now()}`,
        'institution',
        null,
        'active',
        'Test institution for Phase 2',
        '[]',
        '{}',
        new Date(),
        new Date(),
      ]
    );
    institutionId = instResult.rows[0].id;
  });

  afterAll(async () => {
    // Cleanup
    if (institutionId) {
      try {
        await db.query('DELETE FROM goal_rollup_results WHERE parent_goal_id IN (SELECT id FROM autonomy_goals WHERE institution_id = $1)', [
          institutionId,
        ]);
        await db.query('DELETE FROM autonomy_goals WHERE institution_id = $1', [institutionId]);
        await db.query('DELETE FROM institutions WHERE id = $1', [institutionId]);
      } catch (e) {
        console.warn('Cleanup warning:', e);
      }
    }
  });

  it('creates root goal (depth 0)', async () => {
    expect(institutionId).toBeDefined();

    const rootGoal = await goalHierarchyService.createRootGoal(
      institutionId,
      'Build institutional expertise in AI safety'
    );

    expect(rootGoal.id).toBeDefined();
    expect(rootGoal.goal_depth).toBe(0);
    expect(rootGoal.goal_path).toMatch(/^\//);
    expect(rootGoal.status).toBe('queued');
    expect(rootGoal.institution_id).toBe(institutionId);

    rootGoalId = rootGoal.id;
    console.log(`✅ Root goal created: ${rootGoalId}`);
  });

  it('creates sub-goals (depth 1)', async () => {
    expect(rootGoalId).toBeDefined();

    // Create 2 sub-goals
    const subGoal1 = await goalHierarchyService.createSubGoal(
      rootGoalId,
      'Research competitor AI safety claims'
    );

    const subGoal2 = await goalHierarchyService.createSubGoal(
      rootGoalId,
      'Analyze market trends in AI governance'
    );

    expect(subGoal1.goal_depth).toBe(1);
    expect(subGoal1.parent_goal_id).toBe(rootGoalId);
    expect(subGoal1.goal_path).toContain(rootGoalId);

    expect(subGoal2.goal_depth).toBe(1);
    expect(subGoal2.parent_goal_id).toBe(rootGoalId);

    subGoal1Id = subGoal1.id;
    subGoal2Id = subGoal2.id;

    console.log(`✅ Sub-goals created: ${subGoal1Id}, ${subGoal2Id}`);
  });

  it('creates task goals (depth 2)', async () => {
    expect(subGoal1Id).toBeDefined();

    // Create tasks under sub-goal 1
    const task1 = await goalHierarchyService.createTaskGoal(
      subGoal1Id,
      'Research competitor AI safety claims via web search'
    );

    const task2 = await goalHierarchyService.createTaskGoal(
      subGoal1Id,
      'Analyze sentiment in competitor communications'
    );

    expect(task1.goal_depth).toBe(2);
    expect(task1.parent_goal_id).toBe(subGoal1Id);
    expect(task2.goal_depth).toBe(2);

    taskGoals.push(task1.id, task2.id);

    console.log(`✅ Task goals created: ${task1.id}, ${task2.id}`);
  });

  it('enforces maximum goal depth (max 2)', async () => {
    expect(taskGoals.length).toBeGreaterThan(0);

    // Try to create goal under task goal (should fail, depth would be 3)
    try {
      await goalHierarchyService.createTaskGoal(taskGoals[0], 'Should fail');
      expect(true).toBe(false); // Should not reach here
    } catch (e: any) {
      expect(e.message).toContain('Maximum goal depth is 2');
      console.log(`✅ Maximum depth enforcement working`);
    }
  });

  it('retrieves complete goal hierarchy', async () => {
    expect(institutionId).toBeDefined();

    const hierarchy = await goalHierarchyService.getGoalHierarchy(institutionId);

    expect(hierarchy.root_goal).toBeDefined();
    expect(hierarchy.root_goal.id).toBe(rootGoalId);
    expect(Array.isArray(hierarchy.sub_goals)).toBe(true);
    expect(hierarchy.sub_goals.length).toBeGreaterThanOrEqual(2);
    expect(Array.isArray(hierarchy.task_goals)).toBe(true);
    expect(hierarchy.task_goals.length).toBeGreaterThanOrEqual(2);
    expect(hierarchy.hierarchy_depth).toBe(2);

    console.log(
      `✅ Retrieved hierarchy: root=${hierarchy.root_goal.id}, subs=${hierarchy.sub_goals.length}, tasks=${hierarchy.task_goals.length}`
    );
  });

  it('records evidence deduplication', async () => {
    const sourceEvidenceId = 'evidence_source_' + Date.now();
    const canonicalEvidenceId = 'evidence_canonical_' + Date.now();

    const dedupId = await goalHierarchyService.deduplicateEvidence(
      sourceEvidenceId,
      canonicalEvidenceId,
      [institutionId],
      ['work_req_1', 'work_req_2'],
      0.85
    );

    expect(dedupId).toBeDefined();

    // Verify it was recorded
    const result = await db.query(
      'SELECT * FROM evidence_deduplication_map WHERE id = $1',
      [dedupId]
    );

    expect(result.rows.length).toBe(1);
    const dedup = result.rows[0];
    expect(dedup.evidence_source_id).toBe(sourceEvidenceId);
    expect(dedup.canonical_evidence_id).toBe(canonicalEvidenceId);
    expect(dedup.confidence_score).toBe(0.85);

    console.log(`✅ Evidence deduplication recorded: ${dedupId}`);
  });

  it('shares evidence across institutions', async () => {
    const evidenceId = 'evidence_' + Date.now();
    const institution2Id = 'phase2_test_inst2_' + Date.now();

    // Create second institution for sharing test
    await db.query(
      `INSERT INTO institutions (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
      [
        institution2Id,
        `phase2_test2_${Date.now()}`,
        'institution',
        null,
        'active',
        'Test institution 2',
        '[]',
        '{}',
        new Date(),
        new Date(),
      ]
    );

    const result = await goalHierarchyService.shareEvidenceWithInstitution(
      evidenceId,
      institutionId,
      institution2Id,
      'collaboration'
    );

    expect(result.id).toBeDefined();
    expect(result.status).toBe('pending');

    // Cleanup
    await db.query('DELETE FROM institutions WHERE id = $1', [institution2Id]);

    console.log(`✅ Evidence sharing request created: ${result.id}`);
  });

  it('records specialist allocation decisions', async () => {
    const workRequestId = 'work_req_' + Date.now();
    const departmentId = 'dept_' + Date.now();

    // First, create department record
    await db.query(
      `INSERT INTO departments (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
      [
        departmentId,
        'Test Department',
        'department',
        institutionId,
        'active',
        'Test',
        '[]',
        '{}',
        new Date(),
        new Date(),
      ]
    );

    await goalHierarchyService.recordAllocationDecision(
      workRequestId,
      departmentId,
      'researcher',
      0.75,
      'Allocated based on recent success rate of 75% on similar tasks'
    );

    // Verify recorded
    const result = await db.query(
      'SELECT * FROM specialist_allocation_history WHERE work_request_id = $1',
      [workRequestId]
    );

    expect(result.rows.length).toBe(1);
    expect(result.rows[0].specialist_role).toBe('researcher');
    expect(result.rows[0].allocated_reputation).toBe(0.75);

    // Cleanup
    await db.query('DELETE FROM departments WHERE id = $1', [departmentId]);

    console.log(`✅ Allocation decision recorded`);
  });

  it('records specialist team patterns', async () => {
    const teamComposition = ['researcher', 'data_analyst', 'claim_validator'];
    const performance = 0.82;

    await goalHierarchyService.recordTeamPattern(teamComposition, performance);

    const patterns = await goalHierarchyService.getSuccessfulTeamPatterns();

    expect(Array.isArray(patterns)).toBe(true);
    expect(patterns.length).toBeGreaterThan(0);

    // Find our pattern
    const ourPattern = patterns.find(
      (p) => JSON.stringify(JSON.parse(p.team_composition).sort()) === JSON.stringify(teamComposition.sort())
    );

    expect(ourPattern).toBeDefined();
    expect(ourPattern?.avg_performance).toBeGreaterThan(0);

    console.log(`✅ Team pattern recorded and retrieved`);
  });

  it('retrieves successful team patterns for adaptation', async () => {
    const patterns = await goalHierarchyService.getSuccessfulTeamPatterns();

    expect(Array.isArray(patterns)).toBe(true);

    if (patterns.length > 0) {
      const pattern = patterns[0];
      expect(pattern.team_composition).toBeDefined();
      expect(pattern.success_count).toBeGreaterThan(0);
      expect(pattern.avg_performance).toBeGreaterThan(0);
      expect(pattern.avg_performance).toBeLessThanOrEqual(1);
    }

    console.log(`✅ Retrieved ${patterns.length} successful team patterns`);
  });

  it('creates multi-level goal hierarchy for complete workflow', async () => {
    // Create new institution for complete workflow test
    const instResult = await db.query(
      `INSERT INTO institutions (id, name, entity_type, parent_id, status, purpose, authority_scope, metadata, created_at, updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id`,
      [
        'phase2_workflow_inst_' + Date.now(),
        `phase2_workflow_${Date.now()}`,
        'institution',
        null,
        'active',
        'Workflow test',
        '[]',
        '{}',
        new Date(),
        new Date(),
      ]
    );
    const testInstId = instResult.rows[0].id;

    // Step 1: Create root goal
    const root = await goalHierarchyService.createRootGoal(
      testInstId,
      'Complete AI safety research project'
    );

    // Step 2: Create sub-goals
    const sub1 = await goalHierarchyService.createSubGoal(
      root.id,
      'Phase 1: Research'
    );
    const sub2 = await goalHierarchyService.createSubGoal(
      root.id,
      'Phase 2: Verification'
    );

    // Step 3: Create tasks
    const task1 = await goalHierarchyService.createTaskGoal(
      sub1.id,
      'Search for papers on AI alignment'
    );
    const task2 = await goalHierarchyService.createTaskGoal(
      sub1.id,
      'Analyze findings'
    );
    const task3 = await goalHierarchyService.createTaskGoal(
      sub2.id,
      'Verify research accuracy'
    );

    // Verify hierarchy
    const hierarchy = await goalHierarchyService.getGoalHierarchy(testInstId);

    expect(hierarchy.root_goal.id).toBe(root.id);
    expect(hierarchy.sub_goals.length).toBe(2);
    expect(hierarchy.task_goals.length).toBe(3);

    // Verify paths are correct
    expect(task1.goal_path).toContain(root.id);
    expect(task1.goal_path).toContain(sub1.id);
    expect(task3.goal_path).toContain(sub2.id);

    // Cleanup
    await db.query(
      'DELETE FROM autonomy_goals WHERE institution_id = $1',
      [testInstId]
    );
    await db.query(
      'DELETE FROM institutions WHERE id = $1',
      [testInstId]
    );

    console.log(`✅ Complete goal hierarchy created and verified`);
  });
});
