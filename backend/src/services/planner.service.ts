import { pool } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

/**
 * PHASE 6: Planning and Long-Horizon Task Decomposition
 *
 * Converts goals into executable plans with:
 * - DAG validation for step dependencies
 * - Risk assessment per step
 * - Multi-step decomposition
 * - Checkpoint integration
 */

export interface PlanInput {
  goalId: string;
  plannerAgentId?: string;
  taskId?: string;
  horizon?: number;
  traceId?: string;
  runId?: string;
}

export interface PlanStep {
  stepIndex: number;
  title: string;
  description?: string;
  requiredTools?: string[];
  expectedOutputSchema?: any;
  riskLevel?: 'critical' | 'high' | 'medium' | 'low';
  dependsOnStepIds?: string[];
  checkpointRequired?: boolean;
}

export interface PlanReview {
  reviewerId: string;
  reviewType?: string;
  decision: 'approved' | 'rejected' | 'conditional' | 'deferred';
  issues?: Record<string, any>;
}

class PlannerService {
  /**
   * Create a new plan from a goal
   */
  async createPlan(input: PlanInput): Promise<{ planId: string }> {
    const client = await pool.connect();
    try {
      const planId = uuidv4();

      const result = await client.query(
        `INSERT INTO autonomy_plans
        (id, goal_id, task_id, planner_agent_id, status, trace_id, run_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id`,
        [
          planId,
          input.goalId,
          input.taskId || null,
          input.plannerAgentId || 'system',
          'draft',
          input.traceId || null,
          input.runId || null,
        ]
      );

      // Audit event
      await client.query(
        `INSERT INTO plan_status_events
        (plan_id, previous_status, new_status, actor_type, actor_id, reason, trace_id)
        VALUES ($1, NULL, $2, $3, $4, $5, $6)`,
        [
          planId,
          'draft',
          'system',
          input.plannerAgentId || 'planner',
          'Plan created',
          input.traceId || null,
        ]
      );

      return { planId: result.rows[0].id };
    } finally {
      client.release();
    }
  }

  /**
   * Generate a plan from a goal using decomposition
   */
  async generatePlanFromGoal(goalId: string): Promise<{ planId: string; steps: number }> {
    const client = await pool.connect();
    try {
      // Fetch goal
      const goalResult = await client.query(
        `SELECT id, title, description, risk_level, success_criteria_json FROM autonomy_goals WHERE id = $1`,
        [goalId]
      );

      if (!goalResult.rows.length) throw new Error(`Goal ${goalId} not found`);
      const goal = goalResult.rows[0];

      // Create plan
      const planId = uuidv4();
      const horizon = 5; // Default horizon for decomposition

      await client.query(
        `INSERT INTO autonomy_plans (id, goal_id, status, horizon, risk_level)
        VALUES ($1, $2, $3, $4, $5)`,
        [planId, goalId, 'validating', horizon, goal.risk_level]
      );

      // Decompose into steps based on goal complexity
      const steps = this.decomposeGoal(goal, horizon);

      // Insert steps
      let stepCount = 0;
      for (const step of steps) {
        const stepId = uuidv4();
        await client.query(
          `INSERT INTO autonomy_plan_steps
          (id, plan_id, step_index, title, description, required_tools_json, risk_level,
           depends_on_step_ids)
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
          [
            stepId,
            planId,
            step.stepIndex,
            step.title,
            step.description,
            JSON.stringify(step.requiredTools || []),
            step.riskLevel || 'medium',
            step.dependsOnStepIds ? `{${step.dependsOnStepIds.join(',')}}` : null,
          ]
        );
        stepCount++;
      }

      // Audit
      await client.query(
        `INSERT INTO plan_status_events
        (plan_id, previous_status, new_status, actor_type, reason)
        VALUES ($1, $2, $3, $4, $5)`,
        [planId, 'draft', 'validating', 'planner', `Generated ${stepCount} steps`]
      );

      return { planId, steps: stepCount };
    } finally {
      client.release();
    }
  }

  /**
   * Validate a plan's DAG structure
   */
  async validatePlanDAG(planId: string): Promise<{ valid: boolean; issues: string[] }> {
    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT id, step_index, depends_on_step_ids FROM autonomy_plan_steps
         WHERE plan_id = $1 ORDER BY step_index`,
        [planId]
      );

      const steps: Array<{ id: string; step_index: number; depends_on_step_ids?: string[] }> = result.rows;
      const issues: string[] = [];
      const stepIds = new Set(steps.map((s) => s.id));

      // Check for circular dependencies (simplified: only same-step ref)
      for (const step of steps) {
        const deps = step.depends_on_step_ids || [];
        if (deps.includes(step.id)) {
          issues.push(`Step ${step.step_index} has circular dependency on itself`);
        }

        // Check that all dependencies exist
        for (const depId of deps) {
          if (!stepIds.has(depId)) {
            issues.push(`Step ${step.step_index} depends on non-existent step ${depId}`);
          }
        }
      }

      // Check topological order (each step's deps have lower index)
      const stepIdToIndex = new Map(steps.map((s: { id: string; step_index: number }) => [s.id, s.step_index]));
      for (const step of steps) {
        const deps = step.depends_on_step_ids || [];
        for (const depId of deps) {
          const depIndex = stepIdToIndex.get(depId);
          if (depIndex && depIndex >= step.step_index) {
            issues.push(`Step ${step.step_index} depends on later step ${depIndex}`);
          }
        }
      }

      return { valid: issues.length === 0, issues };
    } finally {
      client.release();
    }
  }

  /**
   * Validate the entire plan (schema + DAG + risk)
   */
  async validatePlan(planId: string): Promise<{ valid: boolean; issues: string[] }> {
    const client = await pool.connect();
    try {
      const all_issues: string[] = [];

      // Validate plan exists and has required fields
      const planResult = await client.query(
        `SELECT status, horizon FROM autonomy_plans WHERE id = $1`,
        [planId]
      );
      if (!planResult.rows.length) {
        return { valid: false, issues: [`Plan ${planId} not found`] };
      }

      const plan = planResult.rows[0];
      if (!plan.horizon || plan.horizon <= 0) {
        all_issues.push(`Plan must have positive horizon (got ${plan.horizon})`);
      }

      // Check step count
      const stepsResult = await client.query(
        `SELECT COUNT(*) as count FROM autonomy_plan_steps WHERE plan_id = $1`,
        [planId]
      );
      const stepCount = parseInt(stepsResult.rows[0].count);
      if (stepCount === 0) {
        all_issues.push('Plan must have at least one step');
      }

      // Validate DAG
      const dag = await this.validatePlanDAG(planId);
      all_issues.push(...dag.issues);

      // Validate risk levels are reasonable
      const riskResult = await client.query(
        `SELECT risk_level FROM autonomy_plan_steps WHERE plan_id = $1 AND risk_level = 'critical'`,
        [planId]
      );
      if (riskResult.rows.length > 2) {
        all_issues.push(`Too many critical steps (${riskResult.rows.length} > 2)`);
      }

      return { valid: all_issues.length === 0, issues: all_issues };
    } finally {
      client.release();
    }
  }

  /**
   * Execute next step in a plan
   */
  async executeNextStep(planId: string, traceId?: string): Promise<{ stepId: string; stepIndex: number }> {
    const client = await pool.connect();
    try {
      // Find next ready step
      const result = await client.query(
        `SELECT id, step_index FROM autonomy_plan_steps
         WHERE plan_id = $1 AND status = 'pending'
         ORDER BY step_index
         LIMIT 1`,
        [planId]
      );

      if (!result.rows.length) {
        throw new Error('No pending steps available');
      }

      const step = result.rows[0];

      // Mark as running
      await client.query(
        `UPDATE autonomy_plan_steps SET status = $1, started_at = NOW(), trace_id = $2
         WHERE id = $3`,
        ['running', traceId || null, step.id]
      );

      return { stepId: step.id, stepIndex: step.step_index };
    } finally {
      client.release();
    }
  }

  /**
   * Mark a step as completed
   */
  async completeStep(stepId: string, output?: any, traceId?: string): Promise<void> {
    const client = await pool.connect();
    try {
      await client.query(
        `UPDATE autonomy_plan_steps SET status = $1, completed_at = NOW(), trace_id = $2
         WHERE id = $3`,
        ['completed', traceId || null, stepId]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Mark a step as failed
   */
  async failStep(stepId: string, reason: string, traceId?: string): Promise<void> {
    const client = await pool.connect();
    try {
      await client.query(
        `UPDATE autonomy_plan_steps SET status = $1, failed_at = NOW(), trace_id = $2
         WHERE id = $3`,
        ['failed', traceId || null, stepId]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Mark a plan as approved
   */
  async approvePlan(planId: string, reviewerId: string): Promise<void> {
    const client = await pool.connect();
    try {
      // Add review record
      await client.query(
        `INSERT INTO plan_reviews (plan_id, reviewer_id, decision)
         VALUES ($1, $2, $3)`,
        [planId, reviewerId, 'approved']
      );

      // Update plan status
      await client.query(
        `UPDATE autonomy_plans SET status = $1, approved_at = NOW()
         WHERE id = $2`,
        ['approved', planId]
      );

      // Audit
      await client.query(
        `INSERT INTO plan_status_events (plan_id, previous_status, new_status, actor_type, actor_id)
         VALUES ($1, $2, $3, $4, $5)`,
        [planId, 'review_required', 'approved', 'governor', reviewerId]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Reject a plan
   */
  async rejectPlan(planId: string, reviewerId: string, reason: string): Promise<void> {
    const client = await pool.connect();
    try {
      await client.query(
        `INSERT INTO plan_reviews (plan_id, reviewer_id, decision, issues_json)
         VALUES ($1, $2, $3, $4)`,
        [planId, reviewerId, 'rejected', JSON.stringify({ reason })]
      );

      await client.query(
        `UPDATE autonomy_plans SET status = $1 WHERE id = $2`,
        ['review_required', planId]
      );

      await client.query(
        `INSERT INTO plan_status_events (plan_id, previous_status, new_status, actor_type, actor_id, reason)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [planId, 'review_required', 'review_required', 'governor', reviewerId, reason]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Activate a plan for execution
   */
  async activatePlan(planId: string): Promise<void> {
    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT status FROM autonomy_plans WHERE id = $1`,
        [planId]
      );

      if (!result.rows.length) throw new Error(`Plan ${planId} not found`);
      if (result.rows[0].status !== 'approved') {
        throw new Error(`Plan must be approved before activation (status: ${result.rows[0].status})`);
      }

      await client.query(
        `UPDATE autonomy_plans SET status = $1, activated_at = NOW() WHERE id = $2`,
        ['active', planId]
      );

      await client.query(
        `INSERT INTO plan_status_events (plan_id, previous_status, new_status, actor_type)
         VALUES ($1, $2, $3, $4)`,
        [planId, 'approved', 'active', 'system']
      );
    } finally {
      client.release();
    }
  }

  /**
   * Complete a plan
   */
  async completePlan(planId: string): Promise<void> {
    const client = await pool.connect();
    try {
      await client.query(
        `UPDATE autonomy_plans SET status = $1, completed_at = NOW() WHERE id = $2`,
        ['completed', planId]
      );

      await client.query(
        `INSERT INTO plan_status_events (plan_id, previous_status, new_status, actor_type)
         VALUES ($1, $2, $3, $4)`,
        [planId, 'active', 'completed', 'system']
      );
    } finally {
      client.release();
    }
  }

  /**
   * Get plan details
   */
  async getPlan(planId: string): Promise<any> {
    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT * FROM autonomy_plans WHERE id = $1`,
        [planId]
      );

      if (!result.rows.length) return null;

      const plan = result.rows[0];
      const stepsResult = await client.query(
        `SELECT * FROM autonomy_plan_steps WHERE plan_id = $1 ORDER BY step_index`,
        [planId]
      );

      return { ...plan, steps: stepsResult.rows };
    } finally {
      client.release();
    }
  }

  /**
   * List plans with filters
   */
  async listPlans(filters: {
    goalId?: string;
    status?: string;
    riskLevel?: string;
  }): Promise<any[]> {
    const client = await pool.connect();
    try {
      let query = 'SELECT * FROM autonomy_plans WHERE 1=1';
      const params: any[] = [];

      if (filters.goalId) {
        params.push(filters.goalId);
        query += ` AND goal_id = $${params.length}`;
      }
      if (filters.status) {
        params.push(filters.status);
        query += ` AND status = $${params.length}`;
      }
      if (filters.riskLevel) {
        params.push(filters.riskLevel);
        query += ` AND risk_level = $${params.length}`;
      }

      const result = await client.query(query, params);
      return result.rows;
    } finally {
      client.release();
    }
  }

  // Private helper: Decompose goal into steps
  private decomposeGoal(goal: any, horizon: number): PlanStep[] {
    const steps: PlanStep[] = [];

    // Simple decomposition strategy based on goal properties
    const successCriteria = goal.success_criteria_json || {};

    // Step 1: Preparation/Setup
    steps.push({
      stepIndex: 1,
      title: 'Setup and Validation',
      description: `Prepare environment for ${goal.title}`,
      requiredTools: ['validation', 'setup'],
      riskLevel: 'low',
      dependsOnStepIds: [],
      checkpointRequired: false,
    });

    // Step 2: Main execution
    steps.push({
      stepIndex: 2,
      title: `Execute ${goal.title}`,
      description: goal.description || 'Execute main objective',
      requiredTools: ['compute', 'tools'],
      riskLevel: goal.risk_level,
      dependsOnStepIds: [], // Depends on step 1 (implicitly)
      checkpointRequired: true,
    });

    // Step 3: Validation/Verification
    steps.push({
      stepIndex: 3,
      title: 'Validate Outcome',
      description: 'Verify success criteria met',
      requiredTools: ['validation', 'metrics'],
      riskLevel: 'low',
      dependsOnStepIds: [],
      checkpointRequired: true,
    });

    // Additional steps based on complexity
    if (horizon > 3) {
      steps.push({
        stepIndex: 4,
        title: 'Optimization',
        description: 'Optimize results',
        requiredTools: ['optimizer'],
        riskLevel: 'medium',
        dependsOnStepIds: [],
        checkpointRequired: false,
      });
    }

    return steps;
  }
}

export const planner = new PlannerService();
