import { db } from '../db/client';
import { trustPolicyService } from './trust-policy.service';

export interface CanaryDeployment {
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
  trace_id?: string;
}

export interface CanaryMetric {
  metric_name: string;
  metric_value: number;
  measurement_time: Date;
  status: 'normal' | 'warning' | 'critical';
}

export class TrustPolicyCanaryService {
  /**
   * Create a new canary deployment for a trust policy
   */
  async createCanary(
    policyId: string,
    canaryScope: Record<string, any>,
    targetAgents: number,
    targetPercentage: number,
    traceId?: string
  ): Promise<CanaryDeployment> {
    // Get the policy to validate it exists and get previous policy
    const policy = await trustPolicyService.getById(policyId);
    if (!policy) {
      throw new Error(`Policy ${policyId} not found`);
    }

    // Get previous active policy of this type to track rollback target
    const previousPolicy = await trustPolicyService.getActivePolicyOfType(
      policy.policy_type,
      policy.promotion_scope
    );

    const result = await db.query(
      `INSERT INTO policy_canary_deployments (
        policy_id, previous_policy_id, canary_scope_json, target_agents,
        target_percentage, trace_id
      ) VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING *`,
      [policyId, previousPolicy?.id || null, JSON.stringify(canaryScope), targetAgents, targetPercentage, traceId || null]
    );

    return result.rows[0];
  }

  /**
   * Start a canary deployment
   */
  async startCanary(canaryId: string, traceId?: string): Promise<CanaryDeployment> {
    const result = await db.query(
      `UPDATE policy_canary_deployments
       SET status = 'running'
       WHERE id = $1
       RETURNING *`,
      [canaryId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    return result.rows[0];
  }

  /**
   * Record a metric during canary deployment
   */
  async recordMetric(
    canaryId: string,
    metricName: string,
    metricValue: number,
    status: 'normal' | 'warning' | 'critical' = 'normal'
  ): Promise<void> {
    // Get canary deployment
    const canaryResult = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    if (canaryResult.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    const canary = canaryResult.rows[0];

    // Update metrics JSON
    const currentMetrics = canary.metrics_json || {};
    currentMetrics[metricName] = {
      value: metricValue,
      status: status,
      recorded_at: new Date().toISOString()
    };

    await db.query(
      `UPDATE policy_canary_deployments SET metrics_json = $1 WHERE id = $2`,
      [JSON.stringify(currentMetrics), canaryId]
    );
  }

  /**
   * Evaluate canary health and determine if it should proceed or rollback
   */
  async evaluateCanary(canaryId: string): Promise<{ should_rollback: boolean; reason?: string }> {
    const canaryResult = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    if (canaryResult.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    const canary = canaryResult.rows[0];
    const metrics = canary.metrics_json || {};

    // Check for critical issues that should trigger rollback
    for (const [metricName, metricData] of Object.entries(metrics)) {
      const data = metricData as any;

      // Critical metrics force rollback
      if (data.status === 'critical') {
        return {
          should_rollback: true,
          reason: `Critical metric: ${metricName} = ${data.value}`
        };
      }

      // Specific failure conditions
      if (metricName === 'calibration_regression' && data.value > 0.05) {
        return {
          should_rollback: true,
          reason: `Calibration regression exceeds 5%: ${data.value}`
        };
      }

      if (metricName === 'false_positive_impact' && data.value > 0.20) {
        return {
          should_rollback: true,
          reason: `False positive impact exceeds 20%: ${data.value}`
        };
      }

      if (metricName === 'safety_threshold_compliance' && data.value < 0.95) {
        return {
          should_rollback: true,
          reason: `Safety compliance below 95%: ${data.value}`
        };
      }
    }

    // If no critical issues, canary is healthy
    return { should_rollback: false };
  }

  /**
   * Promote canary to full rollout (activate policy)
   */
  async promoteCanary(canaryId: string, traceId?: string): Promise<void> {
    const canaryResult = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    if (canaryResult.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    const canary = canaryResult.rows[0];

    // Activate the policy (replace previous)
    await trustPolicyService.activateFromCanary(canary.policy_id, traceId);

    // Mark canary as completed
    await db.query(
      `UPDATE policy_canary_deployments SET status = 'completed', ended_at = NOW() WHERE id = $1`,
      [canaryId]
    );
  }

  /**
   * Rollback canary and restore previous policy
   */
  async rollback(canaryId: string, reason: string, traceId?: string): Promise<void> {
    const canaryResult = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    if (canaryResult.rows.length === 0) {
      throw new Error(`Canary ${canaryId} not found`);
    }

    const canary = canaryResult.rows[0];

    // Mark canary as rolled back
    await db.query(
      `UPDATE policy_canary_deployments SET status = 'rolled_back', rolled_back_at = NOW() WHERE id = $1`,
      [canaryId]
    );

    // Mark the policy as rolled back
    await db.query(
      `UPDATE trust_policy_versions SET status = 'rolled_back', rolled_back_at = NOW() WHERE id = $1`,
      [canary.policy_id]
    );

    // Restore previous policy if it exists
    if (canary.previous_policy_id) {
      // Deactivate current and reactivate previous
      await db.query(
        `DELETE FROM active_trust_policies WHERE policy_id = $1`,
        [canary.policy_id]
      );

      await db.query(
        `INSERT INTO active_trust_policies (policy_id, policy_type, promotion_scope)
         SELECT id, policy_type, promotion_scope FROM trust_policy_versions
         WHERE id = $1`,
        [canary.previous_policy_id]
      );
    }

    // Record rollback event
    await db.query(
      `INSERT INTO policy_change_events (
        policy_id, event_type, previous_status, new_status, reason, trace_id
      ) VALUES ($1, 'rolled_back_from_canary', 'canary', 'rolled_back', $2, $3)`,
      [canary.policy_id, reason, traceId || null]
    );
  }

  /**
   * Get canary by ID
   */
  async getById(canaryId: string): Promise<CanaryDeployment | null> {
    const result = await db.query(
      `SELECT * FROM policy_canary_deployments WHERE id = $1`,
      [canaryId]
    );

    return result.rows[0] || null;
  }

  /**
   * List active canaries
   */
  async listActive(limit: number = 50): Promise<CanaryDeployment[]> {
    const result = await db.query(
      `SELECT * FROM policy_canary_deployments
       WHERE status IN ('starting', 'running')
       ORDER BY started_at DESC
       LIMIT $1`,
      [limit]
    );

    return result.rows;
  }

  /**
   * List completed canaries
   */
  async listCompleted(limit: number = 50, offset: number = 0): Promise<CanaryDeployment[]> {
    const result = await db.query(
      `SELECT * FROM policy_canary_deployments
       WHERE status IN ('completed', 'rolled_back')
       ORDER BY ended_at DESC
       LIMIT $1 OFFSET $2`,
      [limit, offset]
    );

    return result.rows;
  }

  /**
   * Get canaries for a specific policy
   */
  async getByPolicy(policyId: string): Promise<CanaryDeployment[]> {
    const result = await db.query(
      `SELECT * FROM policy_canary_deployments
       WHERE policy_id = $1
       ORDER BY started_at DESC`,
      [policyId]
    );

    return result.rows;
  }

  /**
   * Check if a canary is within acceptable metrics
   */
  async isHealthy(canaryId: string): Promise<boolean> {
    const evaluation = await this.evaluateCanary(canaryId);
    return !evaluation.should_rollback;
  }
}

export const trustPolicyCanaryService = new TrustPolicyCanaryService();
