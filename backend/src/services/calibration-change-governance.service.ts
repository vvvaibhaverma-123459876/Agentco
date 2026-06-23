import { db } from '../db/client';
import { calibrationConstitutionService } from './calibration-constitution.service';
import { trustPolicyService } from './trust-policy.service';

export interface ChangeRequest {
  id: string;
  requester_entity_id: string;
  change_type: string;
  title: string;
  description?: string;
  affected_tables: string[];
  affected_columns: string[];
  proposed_change_json: Record<string, any>;
  risk_level: string;
  status: string;
  constitution_id?: string;
  requires_rollback_plan: boolean;
  rollback_plan_json?: Record<string, any>;
  created_at: Date;
  approved_by_entity_id?: string;
  approved_at?: Date;
  rejection_reason?: string;
  trace_id?: string;
}

export interface ComplianceCheck {
  id: string;
  change_request_id: string;
  constitution_id: string;
  check_result: string;
  is_compliant: boolean;
  violations: string[];
  protected_surfaces_touched: string[];
}

export interface ChangeApproval {
  id: string;
  change_request_id: string;
  approver_entity_id: string;
  approver_role?: string;
  approval_scope: string;
  decision: 'approved' | 'rejected' | 'deferred';
  reason?: string;
  quorum_required?: number;
  quorum_met?: boolean;
}

export class CalibrationChangeGovernanceService {
  /**
   * Create a new change request
   */
  async createRequest(
    requesterEntityId: string,
    changeType: string,
    title: string,
    proposedChange: Record<string, any>,
    affectedTables: string[] = [],
    affectedColumns: string[] = [],
    description?: string,
    traceId?: string
  ): Promise<ChangeRequest> {
    const result = await db.query(
      `INSERT INTO calibration_change_requests (
        requester_entity_id, change_type, title, description,
        affected_tables, affected_columns, proposed_change_json, trace_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
      RETURNING *`,
      [
        requesterEntityId,
        changeType,
        title,
        description || null,
        affectedTables,
        affectedColumns,
        JSON.stringify(proposedChange),
        traceId || null
      ]
    );

    return result.rows[0];
  }

  /**
   * Classify risk level of a change
   */
  async classifyRisk(changeRequestId: string): Promise<string> {
    const request = await this.getById(changeRequestId);
    if (!request) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    // Determine risk based on affected tables and change type
    let riskLevel = 'low';

    // Critical if touching protected surfaces
    const criticalTables = [
      'eval_ground_truth',
      'resolution_engine_state',
      'roles',
      'permission_grants',
      'eval_gate_thresholds',
      'schema_migrations'
    ];

    for (const table of request.affected_tables) {
      if (criticalTables.includes(table)) {
        riskLevel = 'critical';
        break;
      }
    }

    // High if touching calibration or resolver
    if (riskLevel !== 'critical') {
      const highTables = [
        'autonomy_episodes',
        'prediction_ledger',
        'eval_runs',
        'trace_contexts'
      ];

      for (const table of request.affected_tables) {
        if (highTables.includes(table)) {
          riskLevel = 'high';
          break;
        }
      }
    }

    // Update with classified risk
    await db.query(
      `UPDATE calibration_change_requests SET risk_level = $1 WHERE id = $2`,
      [riskLevel, changeRequestId]
    );

    return riskLevel;
  }

  /**
   * Check if change complies with constitution
   */
  async checkConstitution(changeRequestId: string): Promise<ComplianceCheck> {
    const request = await this.getById(changeRequestId);
    if (!request) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    const activeConstitution = await calibrationConstitutionService.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    // Validate change against constitution
    const validation = await calibrationConstitutionService.validateChange(
      request.change_type,
      request.affected_tables,
      request.affected_columns
    );

    // Record compliance check
    const result = await db.query(
      `INSERT INTO constitution_compliance_checks (
        change_request_id, constitution_id, check_result, is_compliant,
        violations, protected_surfaces_touched
      ) VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING *`,
      [
        changeRequestId,
        activeConstitution.id,
        validation.is_compliant ? 'COMPLIANT' : 'VIOLATIONS',
        validation.is_compliant,
        validation.violations,
        validation.protected_surfaces_touched.map(ps => ps.surface_name)
      ]
    );

    return result.rows[0];
  }

  /**
   * Run protected surface scan
   */
  async runProtectedSurfaceCheck(changeRequestId: string): Promise<{ blocked: boolean; surfaces: string[] }> {
    const request = await this.getById(changeRequestId);
    if (!request) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    const activeConstitution = await calibrationConstitutionService.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    const protectedSurfaces = await calibrationConstitutionService.getProtectedSurfaces();
    const touchedSurfaces: string[] = [];

    for (const surface of protectedSurfaces) {
      let touched = false;

      // Check tables
      for (const table of surface.table_names || []) {
        if (request.affected_tables.includes(table)) {
          touched = true;
          break;
        }
      }

      // Check columns
      if (!touched) {
        for (const pattern of surface.column_patterns || []) {
          for (const col of request.affected_columns) {
            const regex = new RegExp(pattern);
            if (regex.test(col)) {
              touched = true;
              break;
            }
          }
          if (touched) break;
        }
      }

      if (touched) {
        touchedSurfaces.push(surface.surface_name);
      }
    }

    return {
      blocked: touchedSurfaces.length > 0,
      surfaces: touchedSurfaces
    };
  }

  /**
   * Submit change request for review
   */
  async submitForReview(changeRequestId: string, traceId?: string): Promise<ChangeRequest> {
    // First classify risk and check constitution
    await this.classifyRisk(changeRequestId);
    const compliance = await this.checkConstitution(changeRequestId);

    if (!compliance.is_compliant) {
      throw new Error(`Change request violates constitution: ${compliance.violations.join(', ')}`);
    }

    const protectedCheck = await this.runProtectedSurfaceCheck(changeRequestId);
    if (protectedCheck.blocked) {
      throw new Error(`Change request touches protected surfaces: ${protectedCheck.surfaces.join(', ')}`);
    }

    const result = await db.query(
      `UPDATE calibration_change_requests
       SET status = 'under_review', submitted_for_review_at = NOW()
       WHERE id = $1 AND status = 'draft'
       RETURNING *`,
      [changeRequestId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Change request ${changeRequestId} not found or not in draft status`);
    }

    await this.recordChangeEvent(changeRequestId, 'submitted_for_review', 'draft', 'under_review', traceId);
    return result.rows[0];
  }

  /**
   * Move to impact assessment
   */
  async requestImpactAssessment(changeRequestId: string, traceId?: string): Promise<ChangeRequest> {
    const result = await db.query(
      `UPDATE calibration_change_requests
       SET status = 'impact_assessment', impact_assessment_started_at = NOW()
       WHERE id = $1 AND status = 'under_review'
       RETURNING *`,
      [changeRequestId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Change request ${changeRequestId} not found or not in under_review status`);
    }

    await this.recordChangeEvent(changeRequestId, 'impact_assessment_started', 'under_review', 'impact_assessment', traceId);
    return result.rows[0];
  }

  /**
   * Complete impact assessment and move to approval
   */
  async completeImpactAssessment(changeRequestId: string, traceId?: string): Promise<ChangeRequest> {
    // Check if rollback plan is required and provided
    const request = await this.getById(changeRequestId);
    if (!request) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    if (request.requires_rollback_plan && !request.rollback_plan_json) {
      throw new Error('Rollback plan required but not provided');
    }

    const result = await db.query(
      `UPDATE calibration_change_requests
       SET status = 'approval_required', impact_assessment_completed_at = NOW(), approval_requested_at = NOW()
       WHERE id = $1 AND status = 'impact_assessment'
       RETURNING *`,
      [changeRequestId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Change request ${changeRequestId} not found or not in impact_assessment status`);
    }

    await this.recordChangeEvent(changeRequestId, 'ready_for_approval', 'impact_assessment', 'approval_required', traceId);
    return result.rows[0];
  }

  /**
   * Record governance approval or rejection
   */
  async recordApproval(
    changeRequestId: string,
    approverEntityId: string,
    decision: 'approved' | 'rejected' | 'deferred',
    approvalScope: string,
    reason?: string,
    traceId?: string
  ): Promise<ChangeApproval> {
    // ENFORCE: No self-certification (Rule #2)
    const changeRequest = await this.getById(changeRequestId);
    if (!changeRequest) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    if (changeRequest.requester_entity_id === approverEntityId) {
      throw new Error(`Requester cannot approve their own change request (self-certification prohibited)`);
    }

    const approvalResult = await db.query(
      `INSERT INTO change_approvals (
        change_request_id, approver_entity_id, decision, approval_scope, reason
      ) VALUES ($1, $2, $3, $4, $5)
      RETURNING *`,
      [changeRequestId, approverEntityId, decision, approvalScope, reason || null]
    );

    const approval = approvalResult.rows[0];

    // Update change request status based on decision
    if (decision === 'approved') {
      await db.query(
        `UPDATE calibration_change_requests
         SET status = 'approved', approved_at = NOW(), approved_by_entity_id = $1
         WHERE id = $2`,
        [approverEntityId, changeRequestId]
      );

      await this.recordChangeEvent(changeRequestId, 'approved', 'approval_required', 'approved', traceId);
    } else if (decision === 'rejected') {
      await db.query(
        `UPDATE calibration_change_requests
         SET status = 'rejected', rejected_at = NOW(), rejected_by_entity_id = $1, rejection_reason = $2
         WHERE id = $3`,
        [approverEntityId, reason || null, changeRequestId]
      );

      await this.recordChangeEvent(changeRequestId, 'rejected', 'approval_required', 'rejected', traceId);
    }

    return approval;
  }

  /**
   * Convert approved change request to trust policy
   */
  async convertToPolicy(
    changeRequestId: string,
    policyType: string,
    traceId?: string
  ): Promise<string> {
    const request = await this.getById(changeRequestId);
    if (!request) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    if (request.status !== 'approved') {
      throw new Error(`Change request must be approved to convert to policy (status: ${request.status})`);
    }

    const activeConstitution = await calibrationConstitutionService.getActive();
    if (!activeConstitution) {
      throw new Error('No active constitution found');
    }

    // Create trust policy from change request
    const policy = await trustPolicyService.createDraft(
      policyType,
      activeConstitution.id,
      request.title,
      request.proposed_change_json,
      request.requester_entity_id,
      traceId
    );

    // Record conversion
    await db.query(
      `INSERT INTO change_to_policy_conversions (change_request_id, policy_id)
       VALUES ($1, $2)`,
      [changeRequestId, policy.id]
    );

    return policy.id;
  }

  /**
   * Get change request by ID
   */
  async getById(changeRequestId: string): Promise<ChangeRequest | null> {
    const result = await db.query(
      `SELECT * FROM calibration_change_requests WHERE id = $1`,
      [changeRequestId]
    );

    return result.rows[0] || null;
  }

  /**
   * List change requests by status
   */
  async listByStatus(status: string, limit: number = 20, offset: number = 0): Promise<ChangeRequest[]> {
    const result = await db.query(
      `SELECT * FROM calibration_change_requests
       WHERE status = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [status, limit, offset]
    );

    return result.rows;
  }

  /**
   * Get compliance checks for a change request
   */
  async getComplianceChecks(changeRequestId: string): Promise<ComplianceCheck[]> {
    const result = await db.query(
      `SELECT * FROM constitution_compliance_checks
       WHERE change_request_id = $1
       ORDER BY created_at DESC`,
      [changeRequestId]
    );

    return result.rows;
  }

  /**
   * Get approvals for a change request
   */
  async getApprovals(changeRequestId: string): Promise<ChangeApproval[]> {
    const result = await db.query(
      `SELECT * FROM change_approvals
       WHERE change_request_id = $1
       ORDER BY created_at DESC`,
      [changeRequestId]
    );

    return result.rows;
  }

  /**
   * Get conversion to policy
   */
  async getConversion(changeRequestId: string): Promise<string | null> {
    const result = await db.query(
      `SELECT policy_id FROM change_to_policy_conversions
       WHERE change_request_id = $1
       LIMIT 1`,
      [changeRequestId]
    );

    return result.rows[0]?.policy_id || null;
  }

  /**
   * Set rollback plan for a change request
   */
  async setRollbackPlan(changeRequestId: string, rollbackPlan: Record<string, any>): Promise<ChangeRequest> {
    const result = await db.query(
      `UPDATE calibration_change_requests
       SET rollback_plan_json = $1
       WHERE id = $2
       RETURNING *`,
      [JSON.stringify(rollbackPlan), changeRequestId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Change request ${changeRequestId} not found`);
    }

    return result.rows[0];
  }

  /**
   * Record a change request event
   */
  private async recordChangeEvent(
    changeRequestId: string,
    eventType: string,
    previousStatus: string,
    newStatus: string,
    traceId?: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO change_request_events (
        change_request_id, event_type, previous_status, new_status, trace_id
      ) VALUES ($1, $2, $3, $4, $5)`,
      [changeRequestId, eventType, previousStatus, newStatus, traceId || null]
    );
  }

  /**
   * List pending changes (under review or awaiting approval)
   */
  async listPending(): Promise<ChangeRequest[]> {
    return this.listByStatus('under_review', 50, 0);
  }
}

export const calibrationChangeGovernanceService = new CalibrationChangeGovernanceService();
