import { createHash } from 'crypto';
import { db } from '../db/client';

export interface TrustPolicyVersion {
  id: string;
  policy_type: string;
  constitution_id: string;
  title: string;
  description?: string;
  version_number: number;
  content_json: Record<string, any>;
  content_hash: string;
  signature?: string;
  creator_entity_id?: string;
  parent_policy_id?: string;
  promotion_scope: string;
  status: string;
  created_at: Date;
  submitted_for_review_at?: Date;
  eval_required_at?: Date;
  eval_completed_at?: Date;
  approved_at?: Date;
  rejected_at?: Date;
  canary_started_at?: Date;
  canary_ended_at?: Date;
  activated_at?: Date;
  rolled_back_at?: Date;
  retired_at?: Date;
  trace_id?: string;
}

export interface PolicyEvaluation {
  id: string;
  policy_id: string;
  eval_suite_id?: string;
  eval_run_id?: string;
  passed: boolean;
  calibration_regression: number;
  confidence_shift: number;
  false_positive_impact: number;
  false_negative_impact: number;
  reputation_impact: number;
  dispute_impact: number;
  simulation_leakage_risk: number;
  safety_threshold_compliance: number;
  rollback_feasibility: number;
  audit_completeness: number;
  recommendation: string;
  created_at: Date;
}

export interface PolicyReview {
  id: string;
  policy_id: string;
  reviewer_entity_id?: string;
  reviewer_role?: string;
  decision: 'approved' | 'rejected' | 'conditional';
  reason?: string;
  created_at: Date;
}

export interface PolicyCanary {
  id: string;
  policy_id: string;
  previous_policy_id?: string;
  canary_scope_json: Record<string, any>;
  target_agents: number;
  target_percentage: number;
  status: string;
  metrics_json: Record<string, any>;
  started_at: Date;
  ended_at?: Date;
  rolled_back_at?: Date;
}

export class TrustPolicyService {
  /**
   * Create a new trust policy draft
   */
  async createDraft(
    policyType: string,
    constitutionId: string,
    title: string,
    content: Record<string, any>,
    creatorEntityId?: string,
    traceId?: string
  ): Promise<TrustPolicyVersion> {
    const contentHash = this.hashContent(content);
    const versionNumber = await this.getNextVersionNumber(policyType);

    const result = await db.query(
      `INSERT INTO trust_policy_versions (
        policy_type, constitution_id, title, version_number,
        content_json, content_hash, creator_entity_id, promotion_scope, status, trace_id
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'civilization', 'draft', $8)
      RETURNING *`,
      [policyType, constitutionId, title, versionNumber, JSON.stringify(content), contentHash, creatorEntityId || null, traceId || null]
    );

    return result.rows[0];
  }

  /**
   * Validate policy against constitution
   */
  async validatePolicy(policyId: string, constitutionId: string): Promise<{ isValid: boolean; violations: string[] }> {
    const policy = await this.getById(policyId);
    if (!policy) {
      throw new Error(`Policy ${policyId} not found`);
    }

    const violations: string[] = [];

    // Check policy type is allowed by constitution
    const constitutionCheck = await db.query(
      `SELECT * FROM allowed_change_types
       WHERE constitution_id = $1 AND change_type_name LIKE $2`,
      [constitutionId, `%${policy.policy_type}%`]
    );

    if (constitutionCheck.rows.length === 0) {
      violations.push(`Policy type '${policy.policy_type}' not allowed by constitution`);
    }

    // Check for prohibited change types
    const prohibitedCheck = await db.query(
      `SELECT * FROM prohibited_change_types
       WHERE constitution_id = $1 AND change_type_name LIKE $2`,
      [constitutionId, `%${policy.policy_type}%`]
    );

    if (prohibitedCheck.rows.length > 0) {
      violations.push(`Policy type '${policy.policy_type}' is prohibited by constitution`);
    }

    // Validate content schema
    if (!policy.content_json || typeof policy.content_json !== 'object') {
      violations.push('Policy content must be a valid JSON object');
    }

    return {
      isValid: violations.length === 0,
      violations
    };
  }

  /**
   * Submit policy for review
   */
  async submitForReview(policyId: string, traceId?: string): Promise<TrustPolicyVersion> {
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'under_review', submitted_for_review_at = NOW()
       WHERE id = $1 AND status = 'draft'
       RETURNING *`,
      [policyId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Policy ${policyId} not found or not in draft status`);
    }

    await this.recordChangeEvent(policyId, 'submitted_for_review', 'draft', 'under_review', traceId);
    return result.rows[0];
  }

  /**
   * Mark policy as requiring evaluation
   */
  async requireEval(policyId: string, traceId?: string): Promise<TrustPolicyVersion> {
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'eval_required', eval_required_at = NOW()
       WHERE id = $1 AND status IN ('under_review', 'draft')
       RETURNING *`,
      [policyId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Policy ${policyId} not found or not in draft/under_review status`);
    }

    await this.recordChangeEvent(policyId, 'eval_required', 'under_review', 'eval_required', traceId);
    return result.rows[0];
  }

  /**
   * Record policy evaluation results
   */
  async recordEvaluation(
    policyId: string,
    passed: boolean,
    metrics: Record<string, number>,
    recommendation: string,
    traceId?: string
  ): Promise<PolicyEvaluation> {
    const result = await db.query(
      `INSERT INTO policy_evaluations (
        policy_id, passed, calibration_regression, confidence_shift,
        false_positive_impact, false_negative_impact, reputation_impact,
        dispute_impact, simulation_leakage_risk, safety_threshold_compliance,
        rollback_feasibility, audit_completeness, recommendation
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
      RETURNING *`,
      [
        policyId,
        passed,
        metrics.calibration_regression || 0,
        metrics.confidence_shift || 0,
        metrics.false_positive_impact || 0,
        metrics.false_negative_impact || 0,
        metrics.reputation_impact || 0,
        metrics.dispute_impact || 0,
        metrics.simulation_leakage_risk || 0,
        metrics.safety_threshold_compliance || 0,
        metrics.rollback_feasibility || 0,
        metrics.audit_completeness || 0,
        recommendation
      ]
    );

    // Update policy status based on evaluation result
    const newStatus = passed ? 'approved' : 'eval_failed';
    await db.query(
      `UPDATE trust_policy_versions
       SET status = $1, eval_completed_at = NOW()
       WHERE id = $2`,
      [newStatus, policyId]
    );

    await this.recordChangeEvent(
      policyId,
      'eval_completed',
      'eval_required',
      newStatus,
      traceId
    );

    return result.rows[0];
  }

  /**
   * Approve a policy
   */
  async approve(policyId: string, reviewerEntityId?: string, reason?: string, traceId?: string): Promise<TrustPolicyVersion> {
    // Record review
    await db.query(
      `INSERT INTO policy_reviews (policy_id, reviewer_entity_id, decision, reason, trace_id)
       VALUES ($1, $2, 'approved', $3, $4)`,
      [policyId, reviewerEntityId || null, reason || null, traceId || null]
    );

    // Update policy
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'approved', approved_at = NOW()
       WHERE id = $1 AND status IN ('eval_required', 'eval_failed')
       RETURNING *`,
      [policyId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Policy ${policyId} not found or not in evaluation status`);
    }

    await this.recordChangeEvent(policyId, 'approved', 'eval_required', 'approved', traceId);
    return result.rows[0];
  }

  /**
   * Reject a policy
   */
  async reject(policyId: string, reviewerEntityId?: string, reason?: string, traceId?: string): Promise<TrustPolicyVersion> {
    // Record review
    await db.query(
      `INSERT INTO policy_reviews (policy_id, reviewer_entity_id, decision, reason, trace_id)
       VALUES ($1, $2, 'rejected', $3, $4)`,
      [policyId, reviewerEntityId || null, reason || null, traceId || null]
    );

    // Update policy
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'eval_failed', rejected_at = NOW()
       WHERE id = $1 AND status IN ('under_review', 'eval_required')
       RETURNING *`,
      [policyId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Policy ${policyId} not found or not in under_review/eval_required status`);
    }

    await this.recordChangeEvent(policyId, 'rejected', 'eval_required', 'eval_failed', traceId);
    return result.rows[0];
  }

  /**
   * Start a canary deployment for a policy
   */
  async startCanary(
    policyId: string,
    canaryScope: Record<string, any>,
    targetAgents: number,
    targetPercentage: number,
    traceId?: string
  ): Promise<PolicyCanary> {
    // Get previous active policy to track rollback
    const policy = await this.getById(policyId);
    if (!policy) {
      throw new Error(`Policy ${policyId} not found`);
    }

    const previousPolicy = await this.getActivePolicyOfType(policy.policy_type, policy.promotion_scope);

    const result = await db.query(
      `INSERT INTO policy_canary_deployments (
        policy_id, previous_policy_id, canary_scope_json, target_agents,
        target_percentage, status, trace_id
      ) VALUES ($1, $2, $3, $4, $5, 'running', $6)
      RETURNING *`,
      [policyId, previousPolicy?.id || null, JSON.stringify(canaryScope), targetAgents, targetPercentage, traceId || null]
    );

    // Update policy status
    await db.query(
      `UPDATE trust_policy_versions
       SET status = 'canary', canary_started_at = NOW()
       WHERE id = $1`,
      [policyId]
    );

    await this.recordChangeEvent(policyId, 'canary_started', 'approved', 'canary', traceId);
    return result.rows[0];
  }

  /**
   * End canary and activate policy
   */
  async activateFromCanary(policyId: string, traceId?: string): Promise<TrustPolicyVersion> {
    const policy = await this.getById(policyId);
    if (!policy) {
      throw new Error(`Policy ${policyId} not found`);
    }

    // Deactivate any previous policies of this type
    await db.query(
      `DELETE FROM active_trust_policies
       WHERE policy_type = $1 AND promotion_scope = $2`,
      [policy.policy_type, policy.promotion_scope]
    );

    // Activate this policy
    await db.query(
      `INSERT INTO active_trust_policies (policy_id, policy_type, promotion_scope)
       VALUES ($1, $2, $3)`,
      [policyId, policy.policy_type, policy.promotion_scope]
    );

    // Update policy status
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'active', activated_at = NOW(), canary_ended_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [policyId]
    );

    await this.recordChangeEvent(policyId, 'activated', 'canary', 'active', traceId);
    return result.rows[0];
  }

  /**
   * Rollback a policy to previous version
   */
  async rollback(canaryId: string, reason: string, traceId?: string): Promise<TrustPolicyVersion> {
    // Get canary deployment info
    const canaryResult = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    if (canaryResult.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    const canary = canaryResult.rows[0];
    const policyId = canary.policy_id;
    const previousPolicyId = canary.previous_policy_id;

    // Mark canary as rolled back
    await db.query(
      `UPDATE policy_canary_deployments
       SET status = 'rolled_back', rolled_back_at = NOW()
       WHERE id = $1`,
      [canaryId]
    );

    // Mark policy as rolled back
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'rolled_back', rolled_back_at = NOW()
       WHERE id = $1
       RETURNING *`,
      [policyId]
    );

    // Reactivate previous policy if it exists
    if (previousPolicyId) {
      await db.query(
        `DELETE FROM active_trust_policies WHERE id NOT IN (
          SELECT id FROM active_trust_policies WHERE policy_id = $1
        )`
      );

      await db.query(
        `INSERT INTO active_trust_policies (policy_id, policy_type, promotion_scope)
         SELECT id, policy_type, promotion_scope FROM trust_policy_versions
         WHERE id = $1`,
        [previousPolicyId]
      );
    }

    await this.recordChangeEvent(policyId, 'rolled_back', 'active', 'rolled_back', traceId);
    return result.rows[0];
  }

  /**
   * Retire a policy
   */
  async retire(policyId: string, reason?: string, traceId?: string): Promise<TrustPolicyVersion> {
    const result = await db.query(
      `UPDATE trust_policy_versions
       SET status = 'retired', retired_at = NOW()
       WHERE id = $1 AND status != 'active'
       RETURNING *`,
      [policyId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Policy ${policyId} not found or is currently active (cannot retire active policy)`);
    }

    await this.recordChangeEvent(policyId, 'retired', 'rolled_back', 'retired', traceId);
    return result.rows[0];
  }

  /**
   * Get policy by ID
   */
  async getById(policyId: string): Promise<TrustPolicyVersion | null> {
    const result = await db.query(
      `SELECT * FROM trust_policy_versions WHERE id = $1`,
      [policyId]
    );

    return result.rows[0] || null;
  }

  /**
   * Get active policy for a given type and scope
   */
  async getActivePolicyOfType(
    policyType: string,
    promotionScope: string
  ): Promise<TrustPolicyVersion | null> {
    const result = await db.query(
      `SELECT tpv.* FROM trust_policy_versions tpv
       INNER JOIN active_trust_policies atp ON atp.policy_id = tpv.id
       WHERE tpv.policy_type = $1 AND atp.promotion_scope = $2
       ORDER BY atp.activated_at DESC LIMIT 1`,
      [policyType, promotionScope]
    );

    return result.rows[0] || null;
  }

  /**
   * List all policies of a given type
   */
  async listByType(policyType: string, limit: number = 20, offset: number = 0): Promise<TrustPolicyVersion[]> {
    const result = await db.query(
      `SELECT * FROM trust_policy_versions
       WHERE policy_type = $1
       ORDER BY created_at DESC
       LIMIT $2 OFFSET $3`,
      [policyType, limit, offset]
    );

    return result.rows;
  }

  /**
   * Get evaluations for a policy
   */
  async getEvaluations(policyId: string): Promise<PolicyEvaluation[]> {
    const result = await db.query(
      `SELECT * FROM policy_evaluations WHERE policy_id = $1 ORDER BY created_at DESC`,
      [policyId]
    );

    return result.rows;
  }

  /**
   * Get reviews for a policy
   */
  async getReviews(policyId: string): Promise<PolicyReview[]> {
    const result = await db.query(
      `SELECT * FROM policy_reviews WHERE policy_id = $1 ORDER BY created_at DESC`,
      [policyId]
    );

    return result.rows;
  }

  /**
   * Get canary deployments for a policy
   */
  async getCanaries(policyId: string): Promise<PolicyCanary[]> {
    const result = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE policy_id = $1 ORDER BY started_at DESC`,
      [policyId]
    );

    return result.rows;
  }

  /**
   * Record a policy change event
   */
  private async recordChangeEvent(
    policyId: string,
    eventType: string,
    previousStatus: string,
    newStatus: string,
    traceId?: string
  ): Promise<void> {
    await db.query(
      `INSERT INTO policy_change_events (
        policy_id, event_type, previous_status, new_status, trace_id
      ) VALUES ($1, $2, $3, $4, $5)`,
      [policyId, eventType, previousStatus, newStatus, traceId || null]
    );
  }

  /**
   * Get next version number for a policy type
   */
  private async getNextVersionNumber(policyType: string): Promise<number> {
    const result = await db.query(
      `SELECT COALESCE(MAX(version_number), 0) + 1 as next_version
       FROM trust_policy_versions WHERE policy_type = $1`,
      [policyType]
    );

    return result.rows[0].next_version;
  }

  /**
   * Hash content for integrity verification
   */
  private hashContent(content: Record<string, any>): string {
    const jsonString = JSON.stringify(content);
    return createHash('sha256').update(jsonString).digest('hex');
  }

  /**
   * List all active policies
   */
  async listActivePolicies(): Promise<TrustPolicyVersion[]> {
    const result = await db.query(
      `SELECT DISTINCT tpv.* FROM trust_policy_versions tpv
       INNER JOIN active_trust_policies atp ON atp.policy_id = tpv.id
       ORDER BY atp.activated_at DESC`
    );

    return result.rows;
  }

  /**
   * Get policies by type (alias for listByType)
   */
  async getByType(policyType: string): Promise<TrustPolicyVersion[]> {
    return this.listByType(policyType, 50, 0);
  }
}

export const trustPolicyService = new TrustPolicyService();
