import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface WorkRequest {
  id: string;
  institution_id: string;
  department_id: string;
  objective: string;
  required_specialists: Array<{ role: string; priority: number }>;
  budget: {
    tokens: number;
    iterations: number;
    seconds: number;
  };
  verification_required: boolean;
  external_reviewer_id?: string;
  reputation_metric?: string;
  risk_level: 'low' | 'medium' | 'high';
  status: 'queued' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
  autonomy_goal_id?: string;
  created_at: Date;
  updated_at: Date;
  completed_at?: Date;
}

export interface SpecialistPerformance {
  work_request_id: string;
  specialist_role: string;
  evidence_quality_score: number;
  claim_accuracy_score: number;
  efficiency_score: number;
  overall_score: number;
  tokens_used: number;
  iterations_used: number;
  time_elapsed_seconds: number;
}

class InstitutionWorkAssignmentService {
  /**
   * Submit a work request from institution to autonomy system
   */
  async submitWorkRequest(req: {
    institution_id: string;
    department_id: string;
    objective: string;
    required_specialists: Array<{ role: string; priority: number }>;
    budget: {
      tokens: number;
      iterations: number;
      seconds: number;
    };
    verification_required?: boolean;
    external_reviewer_id?: string;
    reputation_metric?: string;
    risk_level?: 'low' | 'medium' | 'high';
  }): Promise<WorkRequest> {
    const requestId = uuidv4();
    const now = new Date();

    try {
      // Validate institution and department exist
      const instResult = await db.query(
        'SELECT id FROM institutions WHERE id = $1 AND status = $2',
        [req.institution_id, 'active']
      );

      if (instResult.rows.length === 0) {
        throw new Error(`Institution not found: ${req.institution_id}`);
      }

      const deptResult = await db.query(
        'SELECT id FROM departments WHERE id = $1 AND parent_id = $2 AND status = $3',
        [req.department_id, req.institution_id, 'active']
      );

      if (deptResult.rows.length === 0) {
        throw new Error(`Department not found or does not belong to institution`);
      }

      // Validate specialists are assigned to department
      for (const spec of req.required_specialists) {
        const assignResult = await db.query(
          'SELECT id FROM institution_specialist_assignments WHERE department_id = $1 AND specialist_role = $2 AND active = TRUE',
          [req.department_id, spec.role]
        );

        if (assignResult.rows.length === 0) {
          throw new Error(
            `Specialist role '${spec.role}' not assigned to department`
          );
        }
      }

      // Create work request
      const result = await db.query(
        `INSERT INTO institution_work_requests
          (id, institution_id, department_id, objective, required_specialists,
           budget_tokens, budget_iterations, budget_seconds, verification_required,
           external_reviewer_id, reputation_metric, risk_level, status, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
         RETURNING *`,
        [
          requestId,
          req.institution_id,
          req.department_id,
          req.objective,
          JSON.stringify(req.required_specialists),
          req.budget.tokens,
          req.budget.iterations,
          req.budget.seconds,
          req.verification_required || false,
          req.external_reviewer_id || null,
          req.reputation_metric || 'evidence_quality',
          req.risk_level || 'low',
          'queued',
          now,
          now,
        ]
      );

      // Record work cycle event
      await this.recordCycleEvent(requestId, 'initialization', 'submitted', {
        objective: req.objective,
        required_specialists: req.required_specialists,
      });

      return this.formatWorkRequest(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to submit work request: ${e}`);
    }
  }

  /**
   * Get work request by ID
   */
  async getWorkRequest(requestId: string): Promise<WorkRequest | null> {
    try {
      const result = await db.query(
        'SELECT * FROM institution_work_requests WHERE id = $1',
        [requestId]
      );

      if (result.rows.length === 0) {
        return null;
      }

      return this.formatWorkRequest(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to get work request: ${e}`);
    }
  }

  /**
   * Get work requests for institution
   */
  async getInstitutionWorkRequests(
    institutionId: string,
    status?: string
  ): Promise<WorkRequest[]> {
    try {
      let query = 'SELECT * FROM institution_work_requests WHERE institution_id = $1';
      const params: any[] = [institutionId];

      if (status) {
        query += ' AND status = $2';
        params.push(status);
      }

      query += ' ORDER BY created_at DESC';

      const result = await db.query(query, params);
      return result.rows.map((row) => this.formatWorkRequest(row));
    } catch (e) {
      throw new Error(`Failed to get institution work requests: ${e}`);
    }
  }

  /**
   * Update work request status
   */
  async updateWorkRequestStatus(
    requestId: string,
    status: string,
    updates?: { autonomy_goal_id?: string; result_summary?: any }
  ): Promise<WorkRequest> {
    try {
      const now = new Date();
      let query =
        'UPDATE institution_work_requests SET status = $1, updated_at = $2';
      const params: any[] = [status, now];
      let paramIndex = 3;

      if (updates?.autonomy_goal_id) {
        query += `, autonomy_goal_id = $${paramIndex}`;
        params.push(updates.autonomy_goal_id);
        paramIndex++;
      }

      if (updates?.result_summary) {
        query += `, result_summary = $${paramIndex}`;
        params.push(JSON.stringify(updates.result_summary));
        paramIndex++;
      }

      if (status === 'completed') {
        query += `, completed_at = $${paramIndex}`;
        params.push(now);
        paramIndex++;
      }

      query += ` WHERE id = $${paramIndex} RETURNING *`;
      params.push(requestId);

      const result = await db.query(query, params);

      if (result.rows.length === 0) {
        throw new Error(`Work request not found: ${requestId}`);
      }

      // Record cycle event
      await this.recordCycleEvent(requestId, 'lifecycle', 'status_changed', {
        new_status: status,
      });

      return this.formatWorkRequest(result.rows[0]);
    } catch (e) {
      throw new Error(`Failed to update work request status: ${e}`);
    }
  }

  /**
   * Record specialist performance after work completion
   */
  async recordSpecialistPerformance(
    workRequestId: string,
    performance: SpecialistPerformance
  ): Promise<void> {
    try {
      const perfId = uuidv4();

      await db.query(
        `INSERT INTO specialist_performance_history
          (id, work_request_id, specialist_role, evidence_quality_score,
           claim_accuracy_score, efficiency_score, overall_score, tokens_used,
           iterations_used, time_elapsed_seconds)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)`,
        [
          perfId,
          workRequestId,
          performance.specialist_role,
          performance.evidence_quality_score,
          performance.claim_accuracy_score,
          performance.efficiency_score,
          performance.overall_score,
          performance.tokens_used,
          performance.iterations_used,
          performance.time_elapsed_seconds,
        ]
      );

      // Update work request with performance data
      await db.query(
        `UPDATE institution_work_requests
         SET specialist_performance = specialist_performance || $1
         WHERE id = $2`,
        [JSON.stringify([performance]), workRequestId]
      );

      // Record cycle event
      await this.recordCycleEvent(workRequestId, 'completion', 'performance_recorded', {
        specialist_role: performance.specialist_role,
        overall_score: performance.overall_score,
      });
    } catch (e) {
      throw new Error(`Failed to record specialist performance: ${e}`);
    }
  }

  /**
   * Assign specialist to department with reputation score
   */
  async assignSpecialistToDepartment(
    institutionId: string,
    departmentId: string,
    specialistRole: string,
    reputationScore: number = 0.0
  ): Promise<{ id: string; status: string }> {
    try {
      const assignId = uuidv4();
      const now = new Date();

      // Check if already assigned
      const existing = await db.query(
        `SELECT id FROM institution_specialist_assignments
         WHERE department_id = $1 AND specialist_role = $2`,
        [departmentId, specialistRole]
      );

      if (existing.rows.length > 0) {
        // Update existing assignment
        await db.query(
          `UPDATE institution_specialist_assignments
           SET reputation_score = $1, active = TRUE, updated_at = $2
           WHERE id = $3`,
          [reputationScore, now, existing.rows[0].id]
        );

        return {
          id: existing.rows[0].id,
          status: 'updated',
        };
      }

      // Create new assignment
      await db.query(
        `INSERT INTO institution_specialist_assignments
          (id, institution_id, department_id, specialist_role, reputation_score,
           active, created_at, updated_at)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8)`,
        [assignId, institutionId, departmentId, specialistRole, reputationScore, true, now, now]
      );

      return {
        id: assignId,
        status: 'created',
      };
    } catch (e) {
      throw new Error(`Failed to assign specialist: ${e}`);
    }
  }

  /**
   * Get specialist assignments for department
   */
  async getDepartmentSpecialists(departmentId: string): Promise<any[]> {
    try {
      const result = await db.query(
        `SELECT specialist_role, reputation_score, active
         FROM institution_specialist_assignments
         WHERE department_id = $1 AND active = TRUE
         ORDER BY reputation_score DESC`,
        [departmentId]
      );

      return result.rows;
    } catch (e) {
      throw new Error(`Failed to get department specialists: ${e}`);
    }
  }

  /**
   * Record work cycle event for audit trail
   */
  private async recordCycleEvent(
    workRequestId: string,
    phase: string,
    eventType: string,
    details: any
  ): Promise<void> {
    try {
      const eventId = uuidv4();
      const now = new Date();

      await db.query(
        `INSERT INTO work_cycle_events
          (id, work_request_id, cycle_phase, event_type, details, timestamp)
         VALUES ($1, $2, $3, $4, $5, $6)`,
        [eventId, workRequestId, phase, eventType, JSON.stringify(details), now]
      );
    } catch (e) {
      // Log but don't fail on event recording error
      console.error(`Failed to record cycle event: ${e}`);
    }
  }

  /**
   * Format database row to WorkRequest type
   */
  private formatWorkRequest(row: any): WorkRequest {
    return {
      id: row.id,
      institution_id: row.institution_id,
      department_id: row.department_id,
      objective: row.objective,
      required_specialists: row.required_specialists || [],
      budget: {
        tokens: row.budget_tokens,
        iterations: row.budget_iterations,
        seconds: row.budget_seconds,
      },
      verification_required: row.verification_required,
      external_reviewer_id: row.external_reviewer_id,
      reputation_metric: row.reputation_metric,
      risk_level: row.risk_level,
      status: row.status,
      autonomy_goal_id: row.autonomy_goal_id,
      created_at: new Date(row.created_at),
      updated_at: new Date(row.updated_at),
      completed_at: row.completed_at ? new Date(row.completed_at) : undefined,
    };
  }
}

export const institutionWorkAssignmentService =
  new InstitutionWorkAssignmentService();
