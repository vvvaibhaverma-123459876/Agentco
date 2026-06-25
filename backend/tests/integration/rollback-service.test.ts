import { describe, it, expect, afterAll } from '@jest/globals';
import { v4 as uuid } from 'uuid';
import { db } from '../../src/db/client';
import { rollback } from '../../src/services/rollback.service';

const RUN = process.env.RUN_LIVE_SMOKE === '1';
const d = RUN ? describe : describe.skip;

d('rollback service active artifact schema (real Postgres)', () => {
  afterAll(async () => { await db.end(); });

  it('snapshots active artifact state and rolls back the active pointer with an immutable audit event', async () => {
    const canaryPlanId = `canary-${uuid()}`;
    const previousArtifactId = await insertArtifact('previous');
    const candidateArtifactId = await insertArtifact('candidate');

    await rollback.updateActiveArtifact(previousArtifactId);
    const snapshotId = await rollback.capturePreDeploymentSnapshot(
      canaryPlanId,
      previousArtifactId,
      candidateArtifactId,
      { baseline_reward: 1.0 },
    );
    await rollback.updateActiveArtifact(candidateArtifactId);

    expect(await rollback.verifyRollback(candidateArtifactId)).toBe(true);

    const snapshot = await rollback.getDeploymentSnapshot(canaryPlanId);
    expect(snapshot.id).toBe(snapshotId);
    expect(snapshot.artifactIdActive).toBe(candidateArtifactId);
    expect(snapshot.artifactIdPrevious).toBe(previousArtifactId);
    expect(snapshot.baselineMetrics.baseline_reward).toBe(1.0);
    expect(snapshot.baselineMetrics.pending_artifact_id).toBe(candidateArtifactId);

    await rollback.triggerRollback(
      canaryPlanId,
      'regression validation failed',
      'human-governor-test',
      { regression_score: 0.2 },
    );

    expect(await rollback.verifyRollback(previousArtifactId)).toBe(true);

    const active = await db.query(
      `SELECT artifact_id, previous_artifact_id, deployed_by, deployment_count
         FROM active_artifacts
        WHERE artifact_type = 'autonomy_policy'`,
    );
    expect(active.rows).toHaveLength(1);
    expect(active.rows[0].artifact_id).toBe(previousArtifactId);
    expect(active.rows[0].previous_artifact_id).toBe(candidateArtifactId);
    expect(active.rows[0].deployed_by).toBe('human-governor-test');
    expect(Number(active.rows[0].deployment_count)).toBeGreaterThanOrEqual(3);

    const events = await rollback.getRollbackHistory(canaryPlanId);
    expect(events).toHaveLength(1);
    expect(events[0].from).toBe(candidateArtifactId);
    expect(events[0].to).toBe(previousArtifactId);
    expect(events[0].reason).toBe('regression validation failed');
    expect(events[0].triggeredBy).toBe('human-governor-test');

    await expect(db.query(
      `UPDATE canary_rollback_events
          SET reason = 'mutated'
        WHERE canary_plan_id = $1`,
      [canaryPlanId],
    )).rejects.toThrow(/append-only|immutable|immutability/i);
  });
});

async function insertArtifact(label: string): Promise<string> {
  const artifactHash = `rollback_${label}_${uuid()}`;
  const result = await db.query(
    `INSERT INTO artifacts (
       artifact_type, artifact_hash, artifact_json, lineage_json, is_simulation_derived, status
     ) VALUES ('heuristic_update', $1, $2, $3, false, 'promoted')
     RETURNING id`,
    [
      artifactHash,
      JSON.stringify({ type: 'rollback_service_test', label }),
      JSON.stringify({ source: 'rollback_service_test' }),
    ],
  );
  return String(result.rows[0].id);
}
