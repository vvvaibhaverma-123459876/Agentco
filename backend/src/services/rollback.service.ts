import { db } from '../db/client';
import type { PoolClient } from 'pg';
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
    const previousArtifactResult = await db.query(
      `SELECT artifact_id, previous_artifact_id
         FROM active_artifacts
        WHERE artifact_type = 'autonomy_policy'
        LIMIT 1`
    );

    const previousArtifactId = previousArtifactResult.rows.length > 0
      ? String(previousArtifactResult.rows[0].artifact_id)
      : currentActiveArtifactId;

    const result = await db.query(
      `INSERT INTO deployment_snapshots (
        canary_plan_id, artifact_id_active, artifact_id_previous,
        policy_version, baseline_metrics_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
       RETURNING id`,
      [
        canaryPlanId,
        newArtifactId,
        previousArtifactId,
        '1.0',
        JSON.stringify({
          ...(baselineMetrics || {}),
          pending_artifact_id: newArtifactId,
        }),
      ]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to create deployment snapshot');
    }

    const snapshotId = String(result.rows[0].id);
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
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await this.updateActiveArtifactWithClient(client, artifactId, artifactType, 'rollback_service');
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  private async updateActiveArtifactWithClient(
    client: PoolClient,
    artifactId: string,
    artifactType: string = 'autonomy_policy',
    deployedBy: string = 'rollback_service',
  ): Promise<void> {
    const currentResult = await client.query(
      `SELECT artifact_id FROM active_artifacts WHERE artifact_type = $1 FOR UPDATE`,
      [artifactType]
    );
    const currentArtifactId = currentResult.rows.length > 0 ? currentResult.rows[0].artifact_id : null;

    if (currentArtifactId === artifactId) {
      console.log(`[ROLLBACK] Already active: ${artifactId}`);
      return;
    }

    const result = await client.query(
      `UPDATE active_artifacts
       SET artifact_id = $1,
           previous_artifact_id = $2,
           deployed_by = $4,
           deployed_at = NOW(),
           deployment_count = deployment_count + 1
       WHERE artifact_type = $3
       RETURNING artifact_id`,
      [artifactId, currentArtifactId, artifactType, deployedBy]
    );

    if (result.rows.length === 0) {
      await client.query(
        `INSERT INTO active_artifacts (
          artifact_type, artifact_id, previous_artifact_id, deployed_by, deployment_count, deployed_at
        ) VALUES ($1, $2, $3, $4, 1, NOW())`,
        [artifactType, artifactId, currentArtifactId, deployedBy]
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
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const snapshotResult = await client.query(
        `SELECT id, artifact_id_active, artifact_id_previous
           FROM deployment_snapshots
          WHERE canary_plan_id = $1
          ORDER BY created_at DESC
          LIMIT 1
          FOR UPDATE`,
        [canaryPlanId],
      );
      if (snapshotResult.rows.length === 0) {
        throw new Error(`No deployment snapshot found for canary ${canaryPlanId}`);
      }

      const snapshot = snapshotResult.rows[0];
      const artifactIdRolledBackFrom = String(snapshot.artifact_id_active);
      const artifactIdRolledBackTo = String(snapshot.artifact_id_previous);

      await this.updateActiveArtifactWithClient(client, artifactIdRolledBackTo, 'autonomy_policy', triggeredBy);

      await client.query(
        `INSERT INTO canary_rollback_events (
          id, canary_plan_id, deployment_snapshot_id,
          artifact_id_rolled_back_from, artifact_id_rolled_back_to,
          reason, triggered_by, triggered_at, pre_rollback_metrics_json, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), $8, NOW())`,
        [
          uuidv4(),
          canaryPlanId,
          snapshot.id,
          artifactIdRolledBackFrom,
          artifactIdRolledBackTo,
          reason,
          triggeredBy,
          JSON.stringify(preMetrics || {}),
        ]
      );
      await client.query('COMMIT');

      console.log(`[ROLLBACK] Executed rollback for canary ${canaryPlanId}: ${artifactIdRolledBackFrom} → ${artifactIdRolledBackTo}`);
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
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
