import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface RollbackAction {
  canaryPlanId: string;
  artifactIdRolledBackFrom: string;
  artifactIdRolledBackTo: string;
  reason: string;
  triggeredBy: string;
  preRollbackMetrics?: Record<string, any>;
  postRollbackMetrics?: Record<string, any>;
}

/**
 * Rollback Service
 *
 * Handles real artifact rollbacks by:
 * 1. Capturing pre-deployment state
 * 2. Maintaining known-good artifact tracking
 * 3. Performing atomic rollback operations
 * 4. Verifying rollback success
 * 5. Recording audit trail
 */
export class RollbackService {
  /**
   * Create a deployment snapshot before canary deployment
   * Captures current active artifact as "previous_good"
   */
  async capturePreDeploymentSnapshot(
    canaryPlanId: string,
    currentActiveArtifactId: string,
    newArtifactId: string,
    baselineMetrics?: Record<string, any>
  ): Promise<string> {
    // Check if we have a previous artifact to rollback to
    const previousArtifactResult = await db.query(
      `SELECT previous_artifact_id FROM active_artifacts WHERE artifact_type = 'autonomy_policy' LIMIT 1`
    );

    const previousArtifactId =
      previousArtifactResult.rows.length > 0 ? previousArtifactResult.rows[0].previous_artifact_id : null;

    // Create snapshot
    const snapshotId = uuidv4();
    const result = await db.query(
      `INSERT INTO deployment_snapshots (
        canary_plan_id, artifact_id_active, artifact_id_previous,
        policy_version, baseline_metrics_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
       RETURNING id`,
      [
        canaryPlanId,
        currentActiveArtifactId,
        previousArtifactId || currentActiveArtifactId,
        '1.0',
        JSON.stringify(baselineMetrics || {}),
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to create deployment snapshot');
    }

    console.log(`[ROLLBACK] Created snapshot ${snapshotId} for canary ${canaryPlanId}`);
    return snapshotId;
  }

  /**
   * Get deployment snapshot to know what to rollback to
   */
  async getDeploymentSnapshot(canaryPlanId: string): Promise<any> {
    const result = await db.query(
      `SELECT id, artifact_id_active, artifact_id_previous, policy_version,
              baseline_metrics_json, created_at
       FROM deployment_snapshots
       WHERE canary_plan_id = $1
       LIMIT 1`,
      [canaryPlanId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      canaryPlanId,
      artifactIdActive: row.artifact_id_active,
      artifactIdPrevious: row.artifact_id_previous,
      policyVersion: row.policy_version,
      baselineMetrics: row.baseline_metrics_json,
      createdAt: row.created_at,
    };
  }

  /**
   * Update active artifact pointer to a different version
   * This is the REAL state change that performs the rollback
   */
  async updateActiveArtifact(artifactId: string, artifactType: string = 'autonomy_policy'): Promise<void> {
    // Get current active artifact
    const currentResult = await db.query(
      `SELECT artifact_id FROM active_artifacts WHERE artifact_type = $1 FOR UPDATE`,
      [artifactType]
    );

    const currentArtifactId = currentResult.rows.length > 0 ? currentResult.rows[0].artifact_id : null;

    if (currentArtifactId === artifactId) {
      console.log(`[ROLLBACK] Already active: ${artifactId}`);
      return;
    }

    // Update with row-level lock held
    const result = await db.query(
      `UPDATE active_artifacts
       SET artifact_id = $1, previous_artifact_id = $2, deployed_at = NOW(), deployment_count = deployment_count + 1
       WHERE artifact_type = $3
       RETURNING artifact_id`,
      [artifactId, currentArtifactId, artifactType]
    );

    if (result.rows.length === 0) {
      // Create if doesn't exist
      await db.query(
        `INSERT INTO active_artifacts (
          artifact_type, artifact_id, previous_artifact_id, deployed_by, deployment_count
        ) VALUES ($1, $2, $3, $4, 1)`,
        [artifactType, artifactId, currentArtifactId, 'rollback_service']
      );

      console.log(`[ROLLBACK] Created active artifact entry for ${artifactType}`);
    } else {
      console.log(`[ROLLBACK] Updated active artifact to ${artifactId}`);
    }
  }

  /**
   * Execute rollback: change active artifact pointer and record event
   */
  async triggerRollback(
    canaryPlanId: string,
    reason: string,
    triggeredBy: string,
    preMetrics?: Record<string, any>
  ): Promise<void> {
    // Get snapshot to know what to rollback to
    const snapshot = await this.getDeploymentSnapshot(canaryPlanId);
    if (!snapshot) {
      throw new Error(`No deployment snapshot found for canary ${canaryPlanId}`);
    }

    const artifactIdRolledBackFrom = snapshot.artifactIdActive;
    const artifactIdRolledBackTo = snapshot.artifactIdPrevious;

    // Perform atomic rollback (change active artifact pointer)
    await this.updateActiveArtifact(artifactIdRolledBackTo);

    // Record rollback event in audit trail
    const eventId = uuidv4();
    await db.query(
      `INSERT INTO canary_rollback_events (
        id, canary_plan_id, deployment_snapshot_id,
        artifact_id_rolled_back_from, artifact_id_rolled_back_to,
        reason, triggered_by, triggered_at, pre_rollback_metrics_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, NOW())`,
      [
        eventId,
        canaryPlanId,
        snapshot.id,
        artifactIdRolledBackFrom,
        artifactIdRolledBackTo,
        reason,
        triggeredBy,
        JSON.stringify(preMetrics || {}),
      ]
    );

    console.log(`[ROLLBACK] Executed rollback for canary ${canaryPlanId}: ${artifactIdRolledBackFrom} → ${artifactIdRolledBackTo}`);
  }

  /**
   * Verify rollback was successful by checking active artifact
   */
  async verifyRollback(targetArtifactId: string, artifactType: string = 'autonomy_policy'): Promise<boolean> {
    const result = await db.query(
      `SELECT artifact_id FROM active_artifacts WHERE artifact_type = $1`,
      [artifactType]
    );

    if (result.rows.length === 0) {
      return false;
    }

    const activeId = result.rows[0].artifact_id;
    const isRolledBack = activeId === targetArtifactId;

    console.log(
      `[ROLLBACK] Verification: ${isRolledBack ? '✅ SUCCESS' : '❌ FAILED'} - active is ${activeId}, expected ${targetArtifactId}`
    );

    return isRolledBack;
  }

  /**
   * Get rollback history for an artifact
   */
  async getRollbackHistory(canaryPlanId: string, limit: number = 10): Promise<any[]> {
    const result = await db.query(
      `SELECT id, canary_plan_id, artifact_id_rolled_back_from, artifact_id_rolled_back_to,
              reason, triggered_by, triggered_at, pre_rollback_metrics_json
       FROM canary_rollback_events
       WHERE canary_plan_id = $1
       ORDER BY triggered_at DESC
       LIMIT $2`,
      [canaryPlanId, limit]
    );

    return result.rows.map((row: any) => ({
      id: row.id,
      canaryPlanId: row.canary_plan_id,
      from: row.artifact_id_rolled_back_from,
      to: row.artifact_id_rolled_back_to,
      reason: row.reason,
      triggeredBy: row.triggered_by,
      timestamp: row.triggered_at,
    }));
  }
}

// Export singleton instance
export const rollback = new RollbackService();
