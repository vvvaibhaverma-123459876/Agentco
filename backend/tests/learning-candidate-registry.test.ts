import crypto from 'crypto';
import { db } from '../src/db/client';
import { LearnerService } from '../src/services/learner.service';

async function createTrajectory(
  successful: boolean,
  traceId: string,
  isSimulation = false
): Promise<string> {
  const episodeId = crypto.randomUUID();
  const trajectoryId = crypto.randomUUID();
  await db.query(
    `INSERT INTO autonomy_episodes
       (id, run_id, agent_id, title, risk_level, autonomy_level, outcome_status,
        reward_score, trace_id)
     VALUES ($1,$2,$3,$4,'low',1,$5,$6,$7)`,
    [
      episodeId,
      `learner-registry-run-${episodeId}`,
      'learner-registry-test-agent',
      'Learner registry fixture',
      successful ? 'success' : 'partial_success',
      successful ? 1 : 0,
      traceId,
    ]
  );
  await db.query(
    `INSERT INTO trajectory_store
       (id, episode_id, step_index, state_json, action_json, observation_json,
        reward, done, info_json, policy_version, is_successful, is_simulation)
     VALUES ($1,$2,0,$3::jsonb,$4::jsonb,$5::jsonb,$6,true,$7::jsonb,'policy-before', $8, $9)`,
    [
      trajectoryId,
      episodeId,
      JSON.stringify({ task: 'candidate-registry' }),
      JSON.stringify({ action: successful ? 'complete' : 'retry' }),
      JSON.stringify({ outcome: successful ? 'done' : 'partial' }),
      successful ? 1 : 0,
      JSON.stringify({ fixture: true }),
      successful,
      isSimulation,
    ]
  );
  return trajectoryId;
}

describe('learning candidate registry', () => {
  const learner = new LearnerService();

  test('persists learner candidates, artifacts, and event-log lifecycle without deployment', async () => {
    const traceId = crypto.randomUUID();
    const trajectoryIds = [
      await createTrajectory(true, traceId),
      await createTrajectory(false, traceId),
    ];

    const replayBatch = await learner.createReplayBatch({
      trajectoryIds,
      batchLabel: 'candidate-registry-test',
      createdBy: 'learning-candidate-registry-test',
      traceId,
    });
    const run = await learner.runLearner({
      learnerType: 'prompt_update',
      replayBatchId: replayBatch.replayBatchId,
      baselinePolicyVersion: 'policy-before',
      traceId,
    });

    const runDetails = await learner.getLearnerRun(run.learnerRunId);
    expect(runDetails).toMatchObject({
      id: run.learnerRunId,
      replay_batch_id: replayBatch.replayBatchId,
      status: 'in_progress',
      candidate_count: 1,
    });
    expect(runDetails.candidates).toHaveLength(1);

    const candidate = runDetails.candidates[0];
    expect(candidate).toMatchObject({
      learner_run_id: run.learnerRunId,
      candidate_type: 'prompt_update',
      status: 'generated',
      simulation_trained: false,
    });
    expect(candidate.artifact_hash).toMatch(/^[0-9a-f]{64}$/);

    const candidates = await learner.listLearnerCandidates({
      learnerRunId: run.learnerRunId,
      status: 'generated',
      simulationTrained: false,
    });
    expect(candidates.map((row) => row.id)).toContain(candidate.id);

    const artifact = await db.query(
      `SELECT status, artifact_type, is_simulation_derived
         FROM artifacts
        WHERE id = $1`,
      [candidate.artifact_id]
    );
    expect(artifact.rows).toEqual([
      expect.objectContaining({
        status: 'created',
        artifact_type: 'prompt_update',
        is_simulation_derived: false,
      }),
    ]);

    await learner.markCandidateReadyForEval(candidate.id);
    await learner.completeLearnerRun(run.learnerRunId);

    const finalCandidate = await db.query(
      `SELECT status, promoted_at FROM learner_candidates WHERE id = $1`,
      [candidate.id]
    );
    expect(finalCandidate.rows[0]).toMatchObject({ status: 'ready_for_eval', promoted_at: null });

    const finalRun = await db.query(
      `SELECT status, completed_at FROM learner_runs WHERE id = $1`,
      [run.learnerRunId]
    );
    expect(finalRun.rows[0].status).toBe('completed');
    expect(finalRun.rows[0].completed_at).toBeTruthy();

    const events = await db.query(
      `SELECT event_type, object_type, object_id
         FROM event_log
        WHERE correlation_id = $1
        ORDER BY occurred_at ASC`,
      [traceId]
    );
    expect(events.rows).toEqual(expect.arrayContaining([
      expect.objectContaining({
        event_type: 'learner.replay_batch_created',
        object_type: 'replay_batch',
        object_id: replayBatch.replayBatchId,
      }),
      expect.objectContaining({
        event_type: 'learner.run_started',
        object_type: 'learner_run',
        object_id: run.learnerRunId,
      }),
      expect.objectContaining({
        event_type: 'learner.candidate_generated',
        object_type: 'learner_candidate',
        object_id: candidate.id,
      }),
    ]));
  });

  /**
   * Lineage identity regression (G8): identical artifact CONTENT produced from
   * simulation-lineage and real-lineage batches must yield two distinct
   * artifacts, each keeping its own is_simulation_derived flag. Before the
   * fix, hash-only dedup made the real candidate silently adopt the earlier
   * simulation artifact — the exact clean-room failure the audit found.
   */
  async function runCandidateFor(isSimulation: boolean): Promise<{
    artifactId: string; simulationDerived: boolean; artifactHash: string;
  }> {
    const traceId = crypto.randomUUID();
    const trajectoryIds = [
      await createTrajectory(true, traceId, isSimulation),
      await createTrajectory(false, traceId, isSimulation),
    ];
    const batch = await learner.createReplayBatch({
      trajectoryIds,
      batchLabel: `lineage-${isSimulation ? 'sim' : 'real'}`,
      createdBy: 'lineage-identity-test',
      traceId,
    });
    const run = await learner.runLearner({
      learnerType: 'prompt_update',
      replayBatchId: batch.replayBatchId,
      baselinePolicyVersion: 'policy-before',
      traceId,
    });
    const details = await learner.getLearnerRun(run.learnerRunId);
    const candidate = details.candidates[0];
    const artifact = await db.query<{ is_simulation_derived: boolean }>(
      `SELECT is_simulation_derived FROM artifacts WHERE id = $1`,
      [candidate.artifact_id]
    );
    return {
      artifactId: candidate.artifact_id,
      simulationDerived: artifact.rows[0].is_simulation_derived,
      artifactHash: candidate.artifact_hash,
    };
  }

  test('simulation-derived artifact does not contaminate an identical real-lineage artifact (G8)', async () => {
    // Order matters: simulation first, so the old bug would hand its artifact
    // row to the real candidate.
    const sim = await runCandidateFor(true);
    const real = await runCandidateFor(false);

    expect(sim.simulationDerived).toBe(true);
    expect(real.simulationDerived).toBe(false);
    if (sim.artifactHash === real.artifactHash) {
      // Identical content: identity must still split on lineage.
      expect(real.artifactId).not.toBe(sim.artifactId);
    }
  });

  test('mixed simulation/real replay batches are refused outright', async () => {
    const traceId = crypto.randomUUID();
    const trajectoryIds = [
      await createTrajectory(true, traceId, false),
      await createTrajectory(true, traceId, true),
    ];
    await expect(
      learner.createReplayBatch({
        trajectoryIds,
        batchLabel: 'lineage-mixed',
        createdBy: 'lineage-identity-test',
        traceId,
      })
    ).rejects.toThrow(/cannot mix simulation and real/);
  });
});
