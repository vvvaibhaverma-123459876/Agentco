import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

/**
 * Goal Manager Service
 *
 * Manages autonomy goals with lifecycle, budgets, conflicts, and reviews.
 * All goals are controlled by governance rules - agents propose, humans/governors approve.
 */

export interface GoalInput {
  title: string;
  description?: string;
  source: 'agent_proposed' | 'perception_derived' | 'governance_mandated' | 'manual';
  proposedBy: string;
  owningAgentId?: string;
  owningInstitutionId?: string;
  domain: string;
  expectedValue?: number;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  autonomyLevelAllowed: 'L0' | 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6';
  successCriteria: Record<string, any>;
  stopConditions: Record<string, any>;
  traceId?: string;
  runId?: string;
}

export interface GoalBudgetInput {
  computeBudget?: number;
  tokenBudget?: number;
  timeBudgetSeconds?: number;
  toolBudget?: Record<string, any>;
  spendLimit?: number;
}

export interface ReviewInput {
  reviewerId: string;
  reviewerRole: string;
  decision: 'approved' | 'rejected' | 'conditional' | 'deferred';
  reason?: string;
}

export class GoalManager {
  /**
   * Propose a new goal
   */
  async proposeGoal(input: GoalInput): Promise<{goalId: string}> {
    // Validation
    if (!input.title || !input.domain || !input.proposedBy) {
      throw new Error('Missing required fields: title, domain, proposedBy');
    }

    if (!input.successCriteria || Object.keys(input.successCriteria).length === 0) {
      throw new Error('Goal must have success criteria');
    }

    if (!input.stopConditions || Object.keys(input.stopConditions).length === 0) {
      throw new Error('Goal must have stop conditions');
    }

    // Create goal
    const goalId = uuidv4();
    const result = await db.query(
      `INSERT INTO autonomy_goals (
        id, title, description, source, proposed_by,
        owning_agent_id, owning_institution_id, domain,
        expected_value, risk_level, autonomy_level_allowed,
        status, success_criteria_json, stop_conditions_json,
        trace_id, run_id, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, NOW())
       RETURNING id`,
      [
        goalId,
        input.title,
        input.description,
        input.source,
        input.proposedBy,
        input.owningAgentId || null,
        input.owningInstitutionId || null,
        input.domain,
        input.expectedValue || null,
        input.riskLevel,
        // Default to the SAFEST level (L0 = no autonomy) when unspecified; governance
        // raises it later via assignAutonomyLevel(). Never default permissive.
        input.autonomyLevelAllowed || 'L0',
        'proposed',
        JSON.stringify(input.successCriteria),
        JSON.stringify(input.stopConditions),
        input.traceId,
        input.runId,
      ]
    );

    // Record status event
    await this.recordStatusEvent(goalId, null, 'proposed', 'system', 'system', 'Goal proposed');

    console.log(`[GOAL] Goal proposed: ${goalId} (${input.title})`);

    return {goalId: result.rows[0].id};
  }

  /**
   * Attach evidence to goal
   */
  async attachEvidence(
    goalId: string,
    evidenceType: string,
    evidenceRef: string,
    relevanceScore: number,
    provenanceJson?: Record<string, any>
  ): Promise<string> {
    // Verify goal exists
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    const evidenceId = uuidv4();
    const result = await db.query(
      `INSERT INTO goal_evidence (
        id, goal_id, evidence_type, evidence_ref,
        evidence_hash, relevance_score, provenance_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
       RETURNING id`,
      [
        evidenceId,
        goalId,
        evidenceType,
        evidenceRef,
        this.hashEvidence(evidenceRef),
        Math.min(1.0, Math.max(0.0, relevanceScore)),
        JSON.stringify(provenanceJson || {}),
      ]
    );

    console.log(`[GOAL] Evidence attached: ${evidenceId} to goal ${goalId}`);

    return result.rows[0].id;
  }

  /**
   * Classify goal risk level based on domain, expected value, and scope
   */
  async classifyRisk(goalId: string): Promise<'critical' | 'high' | 'medium' | 'low'> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    // Risk classification rules
    const domain = goal.domain.toLowerCase();
    const value = goal.expected_value || 0;

    // Critical: certain domains or high value
    if (['security', 'finance', 'governance', 'safety'].includes(domain) || value > 1000000) {
      return 'critical';
    }

    // High: risky domains or significant value
    if (['medical', 'infrastructure', 'deployment'].includes(domain) || value > 100000) {
      return 'high';
    }

    // Medium: standard business logic
    if (value > 10000) {
      return 'medium';
    }

    // Low: low-impact tasks
    return 'low';
  }

  /**
   * Assign autonomy level based on risk and policy
   */
  async assignAutonomyLevel(goalId: string): Promise<'L0' | 'L1' | 'L2' | 'L3' | 'L4' | 'L5' | 'L6'> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    const risk = goal.risk_level;

    // Rules: autonomy level decreases with risk
    const mapping: Record<string, string> = {
      'critical': 'L0', // Manual only
      'high': 'L1', // Propose only
      'medium': 'L2', // Low-risk logging
      'low': 'L3', // Low/medium-risk notification
    };

    const assigned = mapping[risk] || 'L0';

    // Cannot exceed the goal's allowed level
    const goalAllowed = goal.autonomy_level_allowed;
    const levelRank: Record<string, number> = {
      'L0': 0,
      'L1': 1,
      'L2': 2,
      'L3': 3,
      'L4': 4,
      'L5': 5,
      'L6': 6,
    };

    if (levelRank[assigned] > levelRank[goalAllowed]) {
      return goalAllowed;
    }

    return assigned as any;
  }

  /**
   * Detect conflicts with other active/approved goals
   */
  async detectConflicts(goalId: string): Promise<{conflicts: any[]}> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    // Check for goals in same domain with conflicting scopes
    const result = await db.query(
      `SELECT id, title, domain FROM autonomy_goals
       WHERE domain = $1 AND id != $2
       AND status IN ('active', 'approved', 'under_review')
       LIMIT 10`,
      [goal.domain, goalId]
    );

    const conflicts = result.rows.map(row => ({
      conflictingGoalId: row.id,
      conflictingGoalTitle: row.title,
      conflictType: 'resource_contention',
      severity: 'medium',
    }));

    return {conflicts};
  }

  /**
   * Set budget for goal
   */
  async setBudget(goalId: string, budget: GoalBudgetInput): Promise<string> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    const budgetId = uuidv4();
    const result = await db.query(
      `INSERT INTO goal_budgets (
        id, goal_id, compute_budget, token_budget,
        time_budget_seconds, tool_budget_json, spend_limit, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
       RETURNING id`,
      [
        budgetId,
        goalId,
        budget.computeBudget || null,
        budget.tokenBudget || null,
        budget.timeBudgetSeconds || null,
        JSON.stringify(budget.toolBudget || {}),
        budget.spendLimit || null,
      ]
    );

    console.log(`[GOAL] Budget set for goal ${goalId}`);

    return result.rows[0].id;
  }

  /**
   * Submit goal for review
   */
  async submitForReview(goalId: string): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    if (goal.status !== 'proposed') {
      throw new Error(`Goal must be in 'proposed' status, current: ${goal.status}`);
    }

    // Transition: proposed → under_review
    await db.query(
      `UPDATE autonomy_goals SET status = 'under_review' WHERE id = $1`,
      [goalId]
    );

    await this.recordStatusEvent(goalId, 'proposed', 'under_review', 'system', 'system', 'Submitted for review');

    console.log(`[GOAL] Goal submitted for review: ${goalId}`);
  }

  /**
   * Review goal (approve/reject/conditional)
   */
  async reviewGoal(goalId: string, review: ReviewInput): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    // Cannot self-review your own goal
    if (goal.proposed_by === review.reviewerId) {
      throw new Error('Agent cannot review its own goal');
    }

    // Record review
    await db.query(
      `INSERT INTO goal_reviews (
        id, goal_id, reviewer_id, reviewer_role,
        decision, reason, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, NOW())`,
      [
        uuidv4(),
        goalId,
        review.reviewerId,
        review.reviewerRole,
        review.decision,
        review.reason,
      ]
    );

    // Update goal status based on decision
    let newStatus = goal.status;
    if (review.decision === 'approved') {
      newStatus = 'approved';
    } else if (review.decision === 'rejected') {
      newStatus = 'rejected';
    }

    if (newStatus !== goal.status) {
      await db.query(
        `UPDATE autonomy_goals SET status = $1 WHERE id = $2`,
        [newStatus, goalId]
      );

      await this.recordStatusEvent(goalId, goal.status, newStatus, 'governor', review.reviewerId, `Review: ${review.decision}`);
    }

    console.log(`[GOAL] Goal reviewed: ${goalId} (${review.decision})`);
  }

  /**
   * Activate goal (approved → active)
   */
  async activateGoal(goalId: string): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    if (goal.status !== 'approved') {
      throw new Error(`Goal must be 'approved' to activate, current: ${goal.status}`);
    }

    // Check for conflicts
    const conflicts = await this.detectConflicts(goalId);
    if (conflicts.conflicts.length > 0) {
      throw new Error(`Goal has unresolved conflicts: ${conflicts.conflicts.length}`);
    }

    // Activate
    await db.query(
      `UPDATE autonomy_goals SET status = 'active', activated_at = NOW() WHERE id = $1`,
      [goalId]
    );

    await this.recordStatusEvent(goalId, 'approved', 'active', 'system', 'system', 'Goal activated');

    console.log(`[GOAL] Goal activated: ${goalId}`);
  }

  /**
   * Pause goal
   */
  async pauseGoal(goalId: string, reason: string): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    if (goal.status !== 'active') {
      throw new Error(`Goal must be 'active' to pause, current: ${goal.status}`);
    }

    await db.query(
      `UPDATE autonomy_goals SET status = 'paused' WHERE id = $1`,
      [goalId]
    );

    await this.recordStatusEvent(goalId, 'active', 'paused', 'system', 'system', reason || 'Goal paused');

    console.log(`[GOAL] Goal paused: ${goalId}`);
  }

  /**
   * Complete goal
   */
  async completeGoal(goalId: string, outcomeRef: string): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    if (!['active', 'paused'].includes(goal.status)) {
      throw new Error(`Goal must be 'active' or 'paused' to complete, current: ${goal.status}`);
    }

    await db.query(
      `UPDATE autonomy_goals SET status = 'completed' WHERE id = $1`,
      [goalId]
    );

    await this.recordStatusEvent(goalId, goal.status, 'completed', 'system', 'system', `Completed: ${outcomeRef}`);

    console.log(`[GOAL] Goal completed: ${goalId}`);
  }

  /**
   * Retire goal
   */
  async retireGoal(goalId: string, reason: string): Promise<void> {
    const goal = await this.getGoal(goalId);
    if (!goal) {
      throw new Error(`Goal not found: ${goalId}`);
    }

    // Cannot retire from certain states
    if (['rejected', 'retired'].includes(goal.status)) {
      throw new Error(`Goal in '${goal.status}' status cannot be retired`);
    }

    await db.query(
      `UPDATE autonomy_goals SET status = 'retired', retired_at = NOW() WHERE id = $1`,
      [goalId]
    );

    await this.recordStatusEvent(goalId, goal.status, 'retired', 'system', 'system', reason || 'Goal retired');

    console.log(`[GOAL] Goal retired: ${goalId}`);
  }

  /**
   * List goals with filters
   */
  async listGoals(filters: {status?: string; domain?: string; riskLevel?: string; agentId?: string} = {}): Promise<any[]> {
    let query = 'SELECT * FROM autonomy_goals WHERE 1=1';
    const params: any[] = [];
    let paramIdx = 1;

    if (filters.status) {
      query += ` AND status = $${paramIdx}`;
      params.push(filters.status);
      paramIdx++;
    }

    if (filters.domain) {
      query += ` AND domain = $${paramIdx}`;
      params.push(filters.domain);
      paramIdx++;
    }

    if (filters.riskLevel) {
      query += ` AND risk_level = $${paramIdx}`;
      params.push(filters.riskLevel);
      paramIdx++;
    }

    if (filters.agentId) {
      query += ` AND owning_agent_id = $${paramIdx}`;
      params.push(filters.agentId);
      paramIdx++;
    }

    query += ' ORDER BY created_at DESC';

    const result = await db.query(query, params);
    return result.rows;
  }

  /**
   * Get goal by ID
   */
  async getGoal(goalId: string): Promise<any> {
    const result = await db.query(
      `SELECT * FROM autonomy_goals WHERE id = $1`,
      [goalId]
    );

    return result.rows.length > 0 ? result.rows[0] : null;
  }

  /**
   * Helper: Record status transition event
   */
  private async recordStatusEvent(
    goalId: string,
    previousStatus: string | null,
    newStatus: string,
    actorType: string,
    actorId: string,
    reason: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO goal_status_events (
        id, goal_id, previous_status, new_status,
        actor_type, actor_id, reason, trace_id, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())`,
      [
        uuidv4(),
        goalId,
        previousStatus,
        newStatus,
        actorType,
        actorId,
        reason,
        null, // trace_id
      ]
    );
  }

  /**
   * Helper: Hash evidence for deduplication
   */
  private hashEvidence(evidence: string): string {
    const crypto = require('crypto');
    return crypto.createHash('sha256').update(evidence).digest('hex');
  }
}

export const goalManager = new GoalManager();
