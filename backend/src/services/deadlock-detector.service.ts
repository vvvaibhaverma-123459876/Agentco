import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface GoalLock {
  lock_id: string;
  goal_id: string;
  institution_id: string;
  acquired_by: string;
  acquired_at: Date;
  status: 'active' | 'released';
}

export interface DeadlockIncident {
  id: string;
  institution_id: string;
  goal_ids: string[];
  circular_path: string;
  detected_at: Date;
  resolution_status: 'detected' | 'resolved' | 'escalated';
}

class DeadlockDetectorService {
  /**
   * Acquire exclusive lock on goal execution
   * Returns null if lock already held (non-blocking)
   */
  async acquireGoalLock(
    goalId: string,
    institutionId: string,
    acquiredBy: string
  ): Promise<GoalLock | null> {
    try {
      const existing = await db.query(
        `SELECT id FROM goal_execution_locks
         WHERE goal_id = $1 AND status = 'active'
         LIMIT 1`,
        [goalId]
      );

      if (existing.rows.length > 0) {
        return null;
      }

      const lockId = uuidv4();
      const lockResult = await db.query(
        `INSERT INTO goal_execution_locks
           (id, goal_id, institution_id, acquired_by, acquired_at, status)
         VALUES ($1, $2, $3, $4, $5, 'active')
         RETURNING id, goal_id, institution_id, acquired_by, acquired_at, status`,
        [lockId, goalId, institutionId, acquiredBy, new Date()]
      );
      const lockRow = lockResult.rows[0];
      return {
        lock_id: lockRow.id,
        goal_id: lockRow.goal_id,
        institution_id: lockRow.institution_id,
        acquired_by: lockRow.acquired_by,
        acquired_at: new Date(lockRow.acquired_at),
        status: lockRow.status,
      };
    } catch (e) {
      throw new Error(`Failed to acquire goal lock: ${e}`);
    }
  }

  /**
   * Release goal execution lock
   */
  async releaseGoalLock(lockId: string): Promise<boolean> {
    try {
      const result = await db.query(
        `UPDATE goal_execution_locks
         SET status = 'released', released_at = $2
         WHERE id = $1 AND status = 'active'
         RETURNING id`,
        [lockId, new Date()]
      );

      return result.rows.length > 0;
    } catch (e) {
      throw new Error(`Failed to release goal lock: ${e}`);
    }
  }

  /**
   * Detect circular dependencies in goal execution graph
   */
  async detectCircularDependencies(institutionId: string): Promise<{
    hasCycle: boolean;
    cycle?: string;
  }> {
    try {
      const result = await db.query(
        `SELECT source_goal_id, target_goal_id FROM goal_dependency_graph
         WHERE source_goal_id IN (SELECT id FROM autonomy_goals WHERE institution_id = $1)
            OR target_goal_id IN (SELECT id FROM autonomy_goals WHERE institution_id = $1)`,
        [institutionId]
      );

      const edges = new Map<string, string[]>();
      for (const row of result.rows) {
        const source = row.source_goal_id;
        const target = row.target_goal_id;
        edges.set(source, [...(edges.get(source) || []), target]);
      }
      const visiting = new Set<string>();
      const visited = new Set<string>();
      const stack: string[] = [];
      const visit = (node: string): string[] | null => {
        if (visiting.has(node)) return [...stack, node];
        if (visited.has(node)) return null;
        visiting.add(node);
        stack.push(node);
        for (const next of edges.get(node) || []) {
          const cycle = visit(next);
          if (cycle) return cycle;
        }
        stack.pop();
        visiting.delete(node);
        visited.add(node);
        return null;
      };
      for (const node of edges.keys()) {
        const cycle = visit(node);
        if (cycle) return { hasCycle: true, cycle: cycle.join(' -> ') };
      }
      return { hasCycle: false };
    } catch (e) {
      throw new Error(`Failed to detect circular dependencies: ${e}`);
    }
  }

  /**
   * Record dependency between goals
   */
  async recordDependency(
    sourceGoalId: string,
    targetGoalId: string,
    dependencyType: string
  ): Promise<void> {
    try {
      const depId = uuidv4();

      await db.query(
        `INSERT INTO goal_dependency_graph
          (id, source_goal_id, target_goal_id, dependency_type, detected_at)
         VALUES ($1, $2, $3, $4, $5)`,
        [depId, sourceGoalId, targetGoalId, dependencyType, new Date()]
      );
    } catch (e) {
      throw new Error(`Failed to record dependency: ${e}`);
    }
  }

  /**
   * Record deadlock incident for investigation
   */
  async recordDeadlockIncident(
    institutionId: string,
    goalIds: string[],
    circularPath: string
  ): Promise<DeadlockIncident> {
    try {
      const incidentId = uuidv4();
      const now = new Date();

      const result = await db.query(
        `INSERT INTO deadlock_incidents
          (id, institution_id, goal_ids, circular_path, detected_at, resolution_status)
         VALUES ($1, $2, $3, $4, $5, $6)
         RETURNING *`,
        [
          incidentId,
          institutionId,
          JSON.stringify(goalIds),
          circularPath,
          now,
          'detected',
        ]
      );

      return this.formatDeadlockIncident(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to record deadlock incident: ${e}`);
    }
  }

  /**
   * Resolve deadlock incident
   */
  async resolveDeadlockIncident(
    incidentId: string,
    resolutionMethod: string
  ): Promise<void> {
    try {
      await db.query(
        `UPDATE deadlock_incidents
         SET resolution_status = $1, resolved_at = $2, resolution_method = $3
         WHERE id = $4`,
        ['resolved', new Date(), resolutionMethod, incidentId]
      );
    } catch (e) {
      throw new Error(`Failed to resolve deadlock incident: ${e}`);
    }
  }

  /**
   * Run consistency check on institution state
   */
  async runConsistencyCheck(
    institutionId: string,
    checkType: string
  ): Promise<{
    checkPassed: boolean;
    inconsistencies: any[];
  }> {
    try {
      const inconsistencies: any[] = [];

      if (checkType === 'reputation_consistency') {
        // Check: Institution reputation = aggregate(department reputations)
        const instResult = await db.query(
          'SELECT reputation_score FROM institutions WHERE id = $1',
          [institutionId]
        );

        const deptResult = await db.query(
          `SELECT AVG(reputation_score) as avg_dept_score
           FROM departments
           WHERE parent_id = $1 AND status = 'active'`,
          [institutionId]
        );

        const instScore = instResult.rows[0]?.reputation_score;
        const deptScore = deptResult.rows[0]?.avg_dept_score;

        if (instScore && deptScore && Math.abs(instScore - deptScore) > 0.1) {
          inconsistencies.push({
            type: 'reputation_mismatch',
            institution_score: instScore,
            department_avg: deptScore,
            difference: Math.abs(instScore - deptScore),
          });
        }
      } else if (checkType === 'goal_completion') {
        // Check: Parent goal completed only if all children completed
        const parentResult = await db.query(
          `SELECT id FROM autonomy_goals
           WHERE institution_id = $1 AND status = 'completed' AND goal_depth = 0`,
          [institutionId]
        );

        for (const parent of parentResult.rows) {
          const childResult = await db.query(
            `SELECT COUNT(*) as incomplete_count
             FROM autonomy_goals
             WHERE parent_goal_id = $1 AND status != 'completed'`,
            [parent.id]
          );

          if (childResult.rows[0]?.incomplete_count > 0) {
            inconsistencies.push({
              type: 'incomplete_children',
              parent_goal_id: parent.id,
              incomplete_children: childResult.rows[0].incomplete_count,
            });
          }
        }
      } else if (checkType === 'evidence_consistency') {
        // Check: Evidence referenced in claims exists
        const claimResult = await db.query(
          `SELECT id, support_source_ids FROM autonomy_claims
           WHERE goal_id IN (SELECT id FROM autonomy_goals WHERE institution_id = $1)`,
          [institutionId]
        );

        for (const claim of claimResult.rows) {
          const sourceIds = claim.support_source_ids || [];
          for (const sourceId of sourceIds) {
            const evidenceResult = await db.query(
              `SELECT id FROM autonomy_evidence WHERE id = $1`,
              [sourceId]
            );

            if (evidenceResult.rows.length === 0) {
              inconsistencies.push({
                type: 'missing_evidence',
                claim_id: claim.id,
                missing_evidence_id: sourceId,
              });
            }
          }
        }
      }

      // Record check result
      const checkId = uuidv4();
      await db.query(
        `INSERT INTO consistency_checks
          (id, check_type, institution_id, inconsistency_found, details, checked_at)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [
          checkId,
          checkType,
          institutionId,
          inconsistencies.length > 0,
          JSON.stringify(inconsistencies),
          new Date(),
        ]
      );

      return {
        checkPassed: inconsistencies.length === 0,
        inconsistencies: inconsistencies,
      };
    } catch (e) {
      throw new Error(`Failed to run consistency check: ${e}`);
    }
  }

  /**
   * Get deadlock incidents for institution
   */
  async getDeadlockIncidents(institutionId: string): Promise<DeadlockIncident[]> {
    try {
      const result = await db.query(
        `SELECT * FROM deadlock_incidents
         WHERE institution_id = $1
         ORDER BY detected_at DESC`,
        [institutionId]
      );

      return result.rows.map((row) => this.formatDeadlockIncident(row));
    } catch (e) {
      throw new Error(`Failed to get deadlock incidents: ${e}`);
    }
  }

  /**
   * Get reputation audit log for entity
   */
  async getReputationAuditLog(
    entityId: string,
    entityType: string
  ): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT * FROM reputation_audit_log
         WHERE entity_id = $1 AND entity_type = $2
         ORDER BY audit_timestamp DESC
         LIMIT 100`,
        [entityId, entityType]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to get reputation audit log: ${e}`);
    }
  }

  /**
   * Get governance constraint violations
   */
  async getConstraintViolations(institutionId: string): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT * FROM governance_constraint_violations
         WHERE institution_id = $1 AND resolved_at IS NULL
         ORDER BY detected_at DESC`,
        [institutionId]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to get constraint violations: ${e}`);
    }
  }

  /**
   * Resolve governance constraint violation
   */
  async resolveConstraintViolation(
    violationId: string,
    resolution: string
  ): Promise<void> {
    try {
      await db.query(
        `UPDATE governance_constraint_violations
         SET resolved_at = $1, resolution = $2
         WHERE id = $3`,
        [new Date(), resolution, violationId]
      );
    } catch (e) {
      throw new Error(`Failed to resolve constraint violation: ${e}`);
    }
  }

  private formatDeadlockIncident(row: any): DeadlockIncident {
    return {
      id: row.id,
      institution_id: row.institution_id,
      goal_ids: row.goal_ids || [],
      circular_path: row.circular_path,
      detected_at: new Date(row.detected_at),
      resolution_status: row.resolution_status,
    };
  }
}

export const deadlockDetectorService = new DeadlockDetectorService();
