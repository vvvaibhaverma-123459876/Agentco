/**
 * Team Activation Service Tests
 * =============================
 * Tests specialist role validation, budget enforcement, and lifecycle management
 */

import { describe, it, expect, beforeEach, afterEach } from '@jest/globals';
import { db } from '../src/db/client';
import { TeamActivationService, SpecialistActivationRequest } from '../src/services/team-activation.service';
import { isValidSpecialistRole, SPECIALIST_ROLES } from '../src/types/specialist-roles';
import { v4 as uuidv4 } from 'uuid';

describe('Team Activation Service', () => {
  const teamActivation = new TeamActivationService();

  async function createGoal(id: string, text: string, depth = 0, parentGoalId?: string): Promise<void> {
    await db.query(
      `INSERT INTO autonomy_goals (
        id, title, description, source, domain, expected_value, risk_level,
        autonomy_level_allowed, status, proposed_by, depth, parent_goal_id
      ) VALUES ($1, $2, $3, 'manual', 'test', 0.1, 'low', 'L1', $4, 'jest', $5, $6)`,
      [id, text, text, 'active', depth, parentGoalId || null]
    );
  }

  beforeEach(async () => {
    // Clear test data
    await db.query('TRUNCATE autonomy_team_activations CASCADE');
    await db.query('TRUNCATE autonomy_goals CASCADE');
  });

  afterEach(async () => {
    await db.query('TRUNCATE autonomy_team_activations CASCADE');
    await db.query('TRUNCATE autonomy_goals CASCADE');
  });

  describe('Role Validation', () => {
    it('should validate registered specialist roles', () => {
      expect(isValidSpecialistRole('researcher')).toBe(true);
      expect(isValidSpecialistRole('fetcher')).toBe(true);
      expect(isValidSpecialistRole('evidence_summarizer')).toBe(true);
      expect(isValidSpecialistRole('claim_validator')).toBe(true);
      expect(isValidSpecialistRole('reviewer')).toBe(true);
    });

    it('should reject invalid specialist roles', () => {
      expect(isValidSpecialistRole('invalid_role')).toBe(false);
      expect(isValidSpecialistRole('hacker')).toBe(false);
      expect(isValidSpecialistRole('')).toBe(false);
    });

    it('should have all roles in SPECIALIST_ROLES registry', () => {
      const roleNames = ['researcher', 'fetcher', 'evidence_summarizer', 'claim_validator', 'reviewer'];
      for (const name of roleNames) {
        expect(name in SPECIALIST_ROLES).toBe(true);
      }
    });
  });

  describe('Budget Enforcement', () => {
    it('should enforce token budget limits', async () => {
      const parentGoalId = uuidv4();

      // Create parent goal
      await createGoal(parentGoalId, 'Test goal');

      const request: SpecialistActivationRequest = {
        parentGoalId,
        role: 'researcher',
        objective: 'Test research',
        customBudget: {
          tokens: 100,
          iterations: 10,
          seconds: 60,
        },
      };

      const specialist = await teamActivation.activateSpecialist(request);
      expect(specialist).not.toBeNull();
      expect(specialist?.tokensBudget).toBe(100);

      // Record usage
      await teamActivation.recordTokenUsage(specialist!.specialistId, 50);
      const checkAfterPartial = teamActivation.isBudgetExceeded(specialist!.specialistId);
      expect(checkAfterPartial.exceeded).toBe(false);

      // Exceed budget
      await teamActivation.recordTokenUsage(specialist!.specialistId, 60);
      const checkAfterExceeded = teamActivation.isBudgetExceeded(specialist!.specialistId);
      expect(checkAfterExceeded.exceeded).toBe(true);
      expect(checkAfterExceeded.reason).toContain('Token budget exceeded');
    });

    it('should enforce iteration budget limits', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      const specialist = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'reviewer',
        objective: 'Quick review',
        customBudget: {
          tokens: 1000,
          iterations: 3,
          seconds: 60,
        },
      });

      expect(specialist?.iterationsBudget).toBe(3);

      // Record iterations
      await teamActivation.recordIterationUsage(specialist!.specialistId);
      await teamActivation.recordIterationUsage(specialist!.specialistId);
      const checkAfter2 = teamActivation.isBudgetExceeded(specialist!.specialistId);
      expect(checkAfter2.exceeded).toBe(false);

      // Exceed budget
      await teamActivation.recordIterationUsage(specialist!.specialistId);
      await teamActivation.recordIterationUsage(specialist!.specialistId);
      const checkExceeded = teamActivation.isBudgetExceeded(specialist!.specialistId);
      expect(checkExceeded.exceeded).toBe(true);
      expect(checkExceeded.reason).toContain('Iteration budget exceeded');
    });
  });

  describe('Specialist Lifecycle', () => {
    it('should create specialist instance with correct properties', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      const specialist = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'researcher',
        objective: 'Research AI autonomy',
      });

      expect(specialist).not.toBeNull();
      expect(specialist?.role).toBe('researcher');
      expect(specialist?.objective).toBe('Research AI autonomy');
      expect(specialist?.parentGoalId).toBe(parentGoalId);
      expect(specialist?.startedAt).toBeInstanceOf(Date);
    });

    it('should terminate specialist and record results', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      const specialist = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'fetcher',
        objective: 'Fetch pages',
      });

      const specialistId = specialist!.specialistId;

      // Verify specialist is active
      const beforeTermination = teamActivation.getSpecialist(specialistId);
      expect(beforeTermination).not.toBeUndefined();

      // Terminate specialist
      await teamActivation.terminateSpecialist(specialistId, {
        artifacts: ['art1', 'art2'],
        evidence: ['ev1'],
        claims: ['claim1'],
      });

      // Verify specialist is removed from active list
      const afterTermination = teamActivation.getSpecialist(specialistId);
      expect(afterTermination).toBeUndefined();

      // Verify in database
      const result = await db.query(
        `SELECT status, results FROM autonomy_team_activations WHERE specialist_id = $1`,
        [specialistId]
      );
      expect(result.rows[0].status).toBe('completed');
      expect(result.rows[0].results.artifacts).toHaveLength(2);
    });

    it('should get active specialists for a parent goal', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      // Activate multiple specialists
      const spec1 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'researcher',
        objective: 'Research',
      });

      const spec2 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'fetcher',
        objective: 'Fetch',
      });

      const active = await teamActivation.getActiveSpecialists(parentGoalId);
      expect(active).toHaveLength(2);
      expect(active.map(s => s.specialistId)).toContain(spec1!.specialistId);
      expect(active.map(s => s.specialistId)).toContain(spec2!.specialistId);
    });
  });

  describe('Depth Limits', () => {
    it('should prevent activation beyond depth limit', async () => {
      const rootGoalId = uuidv4();
      await createGoal(rootGoalId, 'Root goal');

      // Create goal at depth 2 (max depth allowed for specialists)
      const level2GoalId = uuidv4();
      await createGoal(level2GoalId, 'Level 2 goal', 2, rootGoalId);

      // Should not allow specialist at depth 2
      const result = await teamActivation.activateSpecialist({
        parentGoalId: level2GoalId,
        role: 'researcher',
        objective: 'Research',
      });

      expect(result).toBeNull();
    });
  });

  describe('Concurrent Specialist Limit', () => {
    it('should prevent more than 3 active specialists per parent', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      // Activate 3 specialists (max)
      const spec1 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'researcher',
        objective: 'Research',
      });
      const spec2 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'fetcher',
        objective: 'Fetch',
      });
      const spec3 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'evidence_summarizer',
        objective: 'Summarize',
      });

      expect(spec1).not.toBeNull();
      expect(spec2).not.toBeNull();
      expect(spec3).not.toBeNull();

      // Try to activate 4th (should fail)
      const spec4 = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'claim_validator',
        objective: 'Validate',
      });

      expect(spec4).toBeNull();
    });
  });

  describe('Result Aggregation', () => {
    it('should aggregate specialist results to parent goal', async () => {
      const parentGoalId = uuidv4();
      const artifactId = uuidv4();
      const actionId = uuidv4();

      // Create parent goal and artifact
      await createGoal(parentGoalId, 'Parent goal');

      await db.query(
        `INSERT INTO autonomy_goal_actions (
          action_id, goal_id, action_type, objective, args, success_criteria,
          risk_level, decided_by, decided_at, status
        ) VALUES ($1, $2, $3, $4, '{}'::jsonb, '[]'::jsonb, $5, $6, NOW(), $7)`,
        [actionId, parentGoalId, 'fetch_page', 'Fetch specialist evidence', 'low', 'jest', 'completed']
      );

      await db.query(
        `INSERT INTO autonomy_evidence (id, action_id, source_id, url, retrieved_at, content_hash, source_type, is_public_access)
         VALUES ($1, $2, $3, $4, NOW(), $5, $6, $7)`,
        [artifactId, actionId, uuidv4(), 'https://example.com', 'hash123', 'web', true]
      );

      // Aggregate results
      await teamActivation.aggregateResults(parentGoalId, {
        activationId: uuidv4(),
        specialistId: uuidv4(),
        role: 'researcher',
        status: 'completed',
        artifacts: [artifactId],
        evidence: [artifactId],
        claims: [],
      });

      // Verify artifact is now linked to parent goal
      const result = await db.query(
        `SELECT goal_id FROM autonomy_evidence WHERE id = $1`,
        [artifactId]
      );
      expect(result.rows[0]?.goal_id).toBe(parentGoalId);
    });
  });

  describe('Default Budgets', () => {
    it('should apply default budgets when not specified', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      const specialist = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'fetcher',
        objective: 'Fetch',
        // No customBudget provided
      });

      const fetcherRole = SPECIALIST_ROLES['fetcher'];
      expect(specialist?.tokensBudget).toBe(fetcherRole.defaultBudgets.tokens);
      expect(specialist?.iterationsBudget).toBe(fetcherRole.defaultBudgets.iterations);
      expect(specialist?.secondsBudget).toBe(fetcherRole.defaultBudgets.seconds);
    });

    it('should override with custom budgets when specified', async () => {
      const parentGoalId = uuidv4();
      await createGoal(parentGoalId, 'Test goal');

      const customBudget = {
        tokens: 999,
        iterations: 777,
        seconds: 555,
      };

      const specialist = await teamActivation.activateSpecialist({
        parentGoalId,
        role: 'researcher',
        objective: 'Research',
        customBudget,
      });

      expect(specialist?.tokensBudget).toBe(999);
      expect(specialist?.iterationsBudget).toBe(777);
      expect(specialist?.secondsBudget).toBe(555);
    });
  });
});
