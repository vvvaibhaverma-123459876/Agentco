import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface GoalNode {
  id: string;
  parent_goal_id?: string;
  institution_id: string;
  objective: string;
  goal_depth: number;
  goal_path: string;
  status: 'queued' | 'in_progress' | 'completed' | 'failed';
  evidence_count: number;
  claim_count: number;
  rollup_status?: 'ready_for_rollup' | 'rolled_up';
  child_evidence_count: number;
  created_at: Date;
  updated_at: Date;
}

export interface GoalHierarchy {
  root_goal: GoalNode;
  sub_goals: GoalNode[];
  task_goals: GoalNode[];
  hierarchy_depth: number;
}

class GoalHierarchyService {
  /**
   * Create root goal for institution (depth 0)
   */
  async createRootGoal(
    institutionId: string,
    objective: string
  ): Promise<GoalNode> {
    const goalId = uuidv4();
    const now = new Date();

    try {
      const result = await db.query(
        `INSERT INTO autonomy_goals
          (id, institution_id, objective, goal_depth, goal_path, status, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING *`,
        [goalId, institutionId, objective, 0, `/${goalId}`, 'queued', now, now]
      );

      return this.formatGoalNode(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to create root goal: ${e}`);
    }
  }

  /**
   * Create sub-goal under parent goal (depth 1)
   */
  async createSubGoal(
    parentGoalId: string,
    objective: string
  ): Promise<GoalNode> {
    try {
      // Get parent goal info
      const parentResult = await db.query(
        'SELECT id, goal_depth, goal_path, institution_id FROM autonomy_goals WHERE id = $1',
        [parentGoalId]
      );

      if (parentResult.rows.length === 0) {
        throw new Error(`Parent goal not found: ${parentGoalId}`);
      }

      const parent = parentResult.rows[0];
      const newDepth = parent.goal_depth + 1;
      const goalId = uuidv4();
      const newPath = `${parent.goal_path}/${goalId}`;
      const now = new Date();

      const result = await db.query(
        `INSERT INTO autonomy_goals
          (id, parent_goal_id, institution_id, objective, goal_depth, goal_path, status, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         RETURNING *`,
        [goalId, parentGoalId, parent.institution_id, objective, newDepth, newPath, 'queued', now, now]
      );

      return this.formatGoalNode(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to create sub-goal: ${e}`);
    }
  }

  /**
   * Create task goal under sub-goal (depth 2)
   */
  async createTaskGoal(
    parentSubGoalId: string,
    objective: string
  ): Promise<GoalNode> {
    try {
      // Get parent sub-goal info
      const parentResult = await db.query(
        'SELECT id, goal_depth, goal_path, institution_id FROM autonomy_goals WHERE id = $1',
        [parentSubGoalId]
      );

      if (parentResult.rows.length === 0) {
        throw new Error(`Parent sub-goal not found: ${parentSubGoalId}`);
      }

      const parent = parentResult.rows[0];

      // Enforce max depth of 2 (root=0, sub=1, task=2)
      if (parent.goal_depth >= 2) {
        throw new Error('Maximum goal depth is 2 (root → sub → task)');
      }

      const newDepth = parent.goal_depth + 1;
      const goalId = uuidv4();
      const newPath = `${parent.goal_path}/${goalId}`;
      const now = new Date();

      const result = await db.query(
        `INSERT INTO autonomy_goals
          (id, parent_goal_id, institution_id, objective, goal_depth, goal_path, status, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
         RETURNING *`,
        [goalId, parentSubGoalId, parent.institution_id, objective, newDepth, newPath, 'queued', now, now]
      );

      return this.formatGoalNode(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to create task goal: ${e}`);
    }
  }

  /**
   * Get full goal hierarchy for institution
   */
  async getGoalHierarchy(institutionId: string): Promise<GoalHierarchy> {
    try {
      // Get root goal
      const rootResult = await db.query(
        'SELECT * FROM autonomy_goals WHERE institution_id = $1 AND goal_depth = 0 ORDER BY created_at DESC LIMIT 1',
        [institutionId]
      );

      if (rootResult.rows.length === 0) {
        throw new Error(`No root goal found for institution: ${institutionId}`);
      }

      const rootGoal = this.formatGoalNode(rootResult.rows[0]);

      // Get all sub-goals
      const subResult = await db.query(
        'SELECT * FROM autonomy_goals WHERE institution_id = $1 AND goal_depth = 1 ORDER BY created_at ASC',
        [institutionId]
      );

      const subGoals = subResult.rows.map((r) => this.formatGoalNode(r));

      // Get all task goals
      const taskResult = await db.query(
        'SELECT * FROM autonomy_goals WHERE institution_id = $1 AND goal_depth = 2 ORDER BY created_at ASC',
        [institutionId]
      );

      const taskGoals = taskResult.rows.map((r) => this.formatGoalNode(r));

      return {
        root_goal: rootGoal,
        sub_goals: subGoals,
        task_goals: taskGoals,
        hierarchy_depth: 2,
      };
    } catch (e) {
      throw new Error(`Failed to get goal hierarchy: ${e}`);
    }
  }

  /**
   * Rollup results from completed child goals to parent
   */
  async rollupGoalResults(parentGoalId: string): Promise<{
    total_evidence: number;
    total_claims: number;
    evidence_quality_avg: number;
    claim_accuracy_avg: number;
  }> {
    try {
      // Get all child goals
      const childResult = await db.query(
        `SELECT id, evidence_count, claim_count
         FROM autonomy_goals
         WHERE parent_goal_id = $1 AND status = 'completed'`,
        [parentGoalId]
      );

      if (childResult.rows.length === 0) {
        throw new Error(`No completed child goals found for: ${parentGoalId}`);
      }

      const children = childResult.rows;
      const totalEvidence = children.reduce((sum, g) => sum + (g.evidence_count || 0), 0);
      const totalClaims = children.reduce((sum, g) => sum + (g.claim_count || 0), 0);

      // Get average quality scores from child evidence
      const qualityResult = await db.query(
        `SELECT
           AVG(ce.confidence_score) as avg_confidence,
           COUNT(*) as count
         FROM autonomy_claims ce
         WHERE ce.goal_id IN (${children.map((_, i) => `$${i + 1}`).join(',')})
         AND ce.status = 'supported'`,
        children.map((c) => c.id)
      );

      const avgConfidence = qualityResult.rows[0]?.avg_confidence || 0.7;

      // Record rollup result
      const rollupId = uuidv4();
      const now = new Date();

      const evidenceQuality = totalEvidence > 0 ? (totalEvidence / (children.length * 10)) * 100 / 100 : 0;
      const claimAccuracy = Math.round(avgConfidence * 100) / 100;
      const completeness = Math.round((children.length / (children.length + 1)) * 100) / 100;

      await db.query(
        `INSERT INTO goal_rollup_results
          (id, parent_goal_id, child_goal_ids, total_evidence_count, total_claim_count,
           evidence_quality_avg, claim_accuracy_avg, rollup_completeness, computed_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          rollupId,
          parentGoalId,
          JSON.stringify(children.map((c) => c.id)),
          totalEvidence,
          totalClaims,
          evidenceQuality,
          claimAccuracy,
          completeness,
          now,
        ]
      );

      // Mark parent as rolled_up
      await db.query(
        'UPDATE autonomy_goals SET rollup_status = $1 WHERE id = $2',
        ['rolled_up', parentGoalId]
      );

      return {
        total_evidence: totalEvidence,
        total_claims: totalClaims,
        evidence_quality_avg: Math.round((totalEvidence / (children.length * 10)) * 100) / 100,
        claim_accuracy_avg: avgConfidence,
      };
    } catch (e) {
      throw new Error(`Failed to rollup goal results: ${e}`);
    }
  }

  /**
   * Record evidence reuse/deduplication
   */
  async deduplicateEvidence(
    sourceEvidenceId: string,
    canonicalEvidenceId: string,
    institutionIds: string[],
    workRequestIds: string[],
    confidence: number
  ): Promise<string> {
    try {
      const dedupId = uuidv4();
      const now = new Date();

      const result = await db.query(
        `INSERT INTO evidence_deduplication_map
          (id, evidence_source_id, canonical_evidence_id, institution_ids, work_request_ids,
           confidence_score, first_seen, is_active)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
         RETURNING id`,
        [
          dedupId,
          sourceEvidenceId,
          canonicalEvidenceId,
          JSON.stringify(institutionIds),
          JSON.stringify(workRequestIds),
          confidence,
          now,
          true,
        ]
      );

      return result.rows[0].id;
    } catch (e) {
      throw new Error(`Failed to record evidence deduplication: ${e}`);
    }
  }

  /**
   * Share evidence across institutions with access control
   */
  async shareEvidenceWithInstitution(
    evidenceId: string,
    sourceInstitutionId: string,
    requestingInstitutionId: string,
    agreementType: string = 'collaboration'
  ): Promise<{ id: string; status: string }> {
    try {
      const accessId = uuidv4();
      const now = new Date();

      const result = await db.query(
        `INSERT INTO cross_institutional_evidence_access
          (id, evidence_id, source_institution_id, requesting_institution_id,
           access_status, agreement_type, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7)
         RETURNING id, access_status`,
        [
          accessId,
          evidenceId,
          sourceInstitutionId,
          requestingInstitutionId,
          'pending',
          agreementType,
          now,
        ]
      );

      return {
        id: result.rows[0].id,
        status: result.rows[0].access_status,
      };
    } catch (e) {
      throw new Error(`Failed to share evidence: ${e}`);
    }
  }

  /**
   * Record specialist allocation decision for learning
   */
  async recordAllocationDecision(
    workRequestId: string,
    departmentId: string,
    specialistRole: string,
    allocatedReputation: number,
    reasoning: string
  ): Promise<void> {
    try {
      const allocId = uuidv4();
      const now = new Date();

      await db.query(
        `INSERT INTO specialist_allocation_history
          (id, work_request_id, department_id, specialist_role, allocated_reputation,
           allocation_reasoning, created_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [allocId, workRequestId, departmentId, specialistRole, allocatedReputation, reasoning, now]
      );
    } catch (e) {
      throw new Error(`Failed to record allocation decision: ${e}`);
    }
  }

  /**
   * Get specialist team patterns for adaptive allocation
   */
  async getSuccessfulTeamPatterns(): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT team_composition, success_count, total_deployments, avg_performance
         FROM specialist_team_patterns
         WHERE total_deployments > 0
         ORDER BY avg_performance DESC
         LIMIT 10`
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to get team patterns: ${e}`);
    }
  }

  /**
   * Record successful team pattern for future allocation
   */
  async recordTeamPattern(
    teamComposition: string[],
    performance: number
  ): Promise<void> {
    try {
      // Check if pattern already exists
      const existing = await db.query(
        `SELECT id FROM specialist_team_patterns
         WHERE team_composition = $1`,
        [JSON.stringify(teamComposition.sort())]
      );

      if (existing.rows.length > 0) {
        // Update existing pattern
        const patternId = existing.rows[0].id;
        await db.query(
          `UPDATE specialist_team_patterns
           SET success_count = success_count + 1,
               total_deployments = total_deployments + 1,
               avg_performance = ($1 * success_count + $2) / total_deployments,
               last_used = CURRENT_TIMESTAMP
           WHERE id = $3`,
          [performance, performance, patternId]
        );
      } else {
        // Create new pattern
        const patternId = uuidv4();
        const now = new Date();

        await db.query(
          `INSERT INTO specialist_team_patterns
            (id, team_composition, success_count, total_deployments, avg_performance, last_used, created_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)`,
          [patternId, JSON.stringify(teamComposition.sort()), 1, 1, performance, now, now]
        );
      }
    } catch (e) {
      throw new Error(`Failed to record team pattern: ${e}`);
    }
  }

  private formatGoalNode(row: any): GoalNode {
    return {
      id: row.id,
      parent_goal_id: row.parent_goal_id,
      institution_id: row.institution_id,
      objective: row.objective,
      goal_depth: row.goal_depth,
      goal_path: row.goal_path,
      status: row.status,
      evidence_count: row.evidence_count || 0,
      claim_count: row.claim_count || 0,
      rollup_status: row.rollup_status,
      child_evidence_count: row.child_evidence_count || 0,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at),
    };
  }
}

export const goalHierarchyService = new GoalHierarchyService();
