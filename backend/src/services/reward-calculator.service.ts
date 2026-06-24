import { pool } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

/**
 * PHASE 7: Outcome Resolution and Reward Calculation
 *
 * Computes reproducible reward scores from:
 * - Objective outcomes
 * - Versioned reward functions
 * - Calculation persistence
 * - Safety penalties
 *
 * All calculations are:
 * - Deterministic (same inputs → same score)
 * - Immutable (written once, never changed)
 * - Auditable (full lineage recorded)
 */

export interface OutcomeInput {
  goalId?: string;
  planId?: string;
  taskId?: string;
  outcomeType: string;
  objectiveResult: any;
  traceId?: string;
}

export interface RewardFunctionDefinition {
  name: string;
  domain: string;
  version: number;
  formula: any;
  owner?: string;
  riskLevel?: 'critical' | 'high' | 'medium' | 'low';
}

class RewardCalculatorService {
  /**
   * Create an outcome record
   */
  async createOutcome(input: OutcomeInput): Promise<{ outcomeId: string }> {
    const client = await pool.connect();
    try {
      const outcomeId = uuidv4();

      const result = await client.query(
        `INSERT INTO autonomy_outcomes
        (id, goal_id, plan_id, task_id, outcome_type, objective_result_json, outcome_status, trace_id)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id`,
        [
          outcomeId,
          input.goalId || null,
          input.planId || null,
          input.taskId || null,
          input.outcomeType,
          JSON.stringify(input.objectiveResult || {}),
          'pending',
          input.traceId || null,
        ]
      );

      return { outcomeId: result.rows[0].id };
    } finally {
      client.release();
    }
  }

  /**
   * Register a reward function (immutable once created)
   */
  async registerRewardFunction(input: RewardFunctionDefinition): Promise<{ functionId: string }> {
    const client = await pool.connect();
    try {
      // Check if this version already exists
      const existing = await client.query(
        `SELECT id FROM reward_functions WHERE name = $1 AND domain = $2 AND version = $3`,
        [input.name, input.domain, input.version]
      );

      if (existing.rows.length) {
        // Return existing ID
        return { functionId: existing.rows[0].id };
      }

      const functionId = uuidv4();

      await client.query(
        `INSERT INTO reward_functions
        (id, name, domain, version, formula_json, owner, risk_level, active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id`,
        [
          functionId,
          input.name,
          input.domain,
          input.version,
          JSON.stringify(input.formula),
          input.owner || null,
          input.riskLevel || 'medium',
          true,
        ]
      );

      return { functionId };
    } finally {
      client.release();
    }
  }

  /**
   * Calculate reward score for an outcome
   *
   * Returns:
   * - reward_score (0-100 scale, higher is better)
   * - regret_score (0-100 scale, higher means more regret)
   * - calculation_details with full breakdown
   */
  async calculateReward(
    outcomeId: string,
    rewardFunctionId: string,
    traceId?: string
  ): Promise<{
    calculationId: string;
    rewardScore: number;
    regretScore: number;
  }> {
    const client = await pool.connect();
    try {
      // Fetch outcome
      const outcomeResult = await client.query(
        `SELECT * FROM autonomy_outcomes WHERE id = $1`,
        [outcomeId]
      );

      if (!outcomeResult.rows.length) {
        throw new Error(`Outcome ${outcomeId} not found`);
      }

      const outcome = outcomeResult.rows[0];

      // Fetch reward function
      const funcResult = await client.query(
        `SELECT formula_json FROM reward_functions WHERE id = $1`,
        [rewardFunctionId]
      );

      if (!funcResult.rows.length) {
        throw new Error(`Reward function ${rewardFunctionId} not found`);
      }

      const formula = funcResult.rows[0].formula_json;

      // Calculate scores
      const { rewardScore, regretScore, details } = this.computeScores(
        outcome.objective_result_json,
        formula
      );

      // Apply safety penalties
      const safetyPenalty = this.calculateSafetyPenalty(outcome, formula);
      const finalRewardScore = Math.max(0, rewardScore - safetyPenalty);

      // Persist calculation (immutable)
      const calculationId = uuidv4();
      await client.query(
        `INSERT INTO reward_calculations
        (id, outcome_id, reward_function_id, reward_score, regret_score, calculation_details_json)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id`,
        [
          calculationId,
          outcomeId,
          rewardFunctionId,
          finalRewardScore,
          regretScore,
          JSON.stringify({
            ...details,
            safetyPenalty,
            originalScore: rewardScore,
          }),
        ]
      );

      // Mark outcome as resolved
      await client.query(
        `UPDATE autonomy_outcomes SET outcome_status = $1, resolved_at = NOW(), resolved_by = $2
         WHERE id = $3`,
        ['resolved', 'reward_calculator', outcomeId]
      );

      return {
        calculationId,
        rewardScore: finalRewardScore,
        regretScore,
      };
    } finally {
      client.release();
    }
  }

  /**
   * Get calculation details
   */
  async getCalculation(calculationId: string): Promise<any> {
    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT * FROM reward_calculations WHERE id = $1`,
        [calculationId]
      );

      return result.rows.length ? result.rows[0] : null;
    } finally {
      client.release();
    }
  }

  /**
   * List reward functions
   */
  async listRewardFunctions(filters?: {
    domain?: string;
    active?: boolean;
  }): Promise<any[]> {
    const client = await pool.connect();
    try {
      let query = 'SELECT * FROM reward_functions WHERE 1=1';
      const params: any[] = [];

      if (filters?.domain) {
        params.push(filters.domain);
        query += ` AND domain = $${params.length}`;
      }
      if (filters?.active !== undefined) {
        params.push(filters.active);
        query += ` AND active = $${params.length}`;
      }

      query += ' ORDER BY name, version DESC';

      const result = await client.query(query, params);
      return result.rows;
    } finally {
      client.release();
    }
  }

  /**
   * Get latest reward function for a domain
   */
  async getLatestRewardFunction(domain: string): Promise<any> {
    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT DISTINCT ON (name) * FROM reward_functions
         WHERE domain = $1 AND active = true
         ORDER BY name, version DESC`,
        [domain]
      );

      return result.rows.length ? result.rows[0] : null;
    } finally {
      client.release();
    }
  }

  /**
   * Audit a calculation (for governance/review)
   */
  async auditCalculation(
    calculationId: string,
    reviewerId: string,
    decision: 'approved' | 'rejected',
    reason?: string
  ): Promise<void> {
    const client = await pool.connect();
    try {
      await client.query(
        `INSERT INTO reward_audit (reward_calculation_id, reviewer_id, decision, reason)
         VALUES ($1, $2, $3, $4)`,
        [calculationId, reviewerId, decision, reason || null]
      );
    } finally {
      client.release();
    }
  }

  /**
   * Calculate average reward across multiple outcomes
   */
  async calculateAverageReward(outcomeIds: string[]): Promise<number> {
    if (outcomeIds.length === 0) return 0;

    const client = await pool.connect();
    try {
      const result = await client.query(
        `SELECT AVG(reward_score) as avg_score FROM reward_calculations
         WHERE outcome_id = ANY($1)`,
        [outcomeIds]
      );

      return result.rows[0]?.avg_score || 0;
    } finally {
      client.release();
    }
  }

  /**
   * Compute base scores from outcome and formula
   *
   * Private: Uses deterministic calculation for reproducibility
   */
  private computeScores(
    objectiveResult: any,
    formula: any
  ): { rewardScore: number; regretScore: number; details: any } {
    const details: any = {};

    // If objectiveResult has explicit score, use it
    if (typeof objectiveResult === 'object' && objectiveResult.score !== undefined) {
      const score = parseFloat(objectiveResult.score);
      return {
        rewardScore: Math.min(100, Math.max(0, score)),
        regretScore: 100 - score,
        details: { method: 'explicit_score', score },
      };
    }

    // Otherwise, evaluate formula
    // Simple formula evaluation: look for success/failure indicators
    let rewardScore = 50; // Default middle ground

    if (objectiveResult.success === true) {
      rewardScore = 90;
    } else if (objectiveResult.success === false) {
      rewardScore = 20;
    }

    // Adjust based on metrics if present
    if (objectiveResult.metrics) {
      const m = objectiveResult.metrics;

      // Quality metric: 0-100 scale
      if (m.quality !== undefined) {
        rewardScore = rewardScore * 0.7 + m.quality * 0.3;
      }

      // Speed metric: bonus if fast
      if (m.executionTimeSeconds !== undefined && m.executionTimeSeconds < 60) {
        rewardScore += 5;
      }

      // Cost metric: penalty if expensive
      if (m.costUSD !== undefined && m.costUSD > 100) {
        rewardScore -= Math.min(20, m.costUSD / 10);
      }
    }

    rewardScore = Math.min(100, Math.max(0, rewardScore));

    return {
      rewardScore,
      regretScore: 100 - rewardScore,
      details: {
        method: 'formula_evaluation',
        baseScore: rewardScore,
      },
    };
  }

  /**
   * Calculate safety penalty
   *
   * Private: Apply penalties for risky outcomes
   */
  private calculateSafetyPenalty(outcome: any, formula: any): number {
    let penalty = 0;

    // Penalty if outcome touched protected surfaces
    if (outcome.objective_result_json?.touched_protected_surfaces) {
      penalty += 15;
    }

    // Penalty if outcome caused unintended effects
    if (outcome.objective_result_json?.side_effects?.count > 0) {
      penalty += outcome.objective_result_json.side_effects.count * 2;
    }

    // Penalty if outcome violated policy
    if (outcome.objective_result_json?.policy_violations?.count > 0) {
      penalty += outcome.objective_result_json.policy_violations.count * 5;
    }

    // Penalty if outcome was in simulation but reporting as real
    if (outcome.objective_result_json?.simulation === true && !outcome.objective_result_json?.labeled_as_simulation) {
      penalty += 20;
    }

    return Math.min(50, penalty); // Cap at 50 point penalty
  }
}

export const rewardCalculator = new RewardCalculatorService();
