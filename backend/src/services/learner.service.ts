import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';
import * as crypto from 'crypto';

export interface LearnerCandidate {
  id: string;
  learnerRunId: string;
  candidateType: 'prompt_update' | 'config_update' | 'heuristic_update' | 'memory_policy_update';
  artifactId: string;
  artifactHash: string;
  metricsBeforeJson: Record<string, number>;
  metricsAfterJson: Record<string, number>;
  improvementPercent: number;
  status: 'created' | 'evaluated' | 'promoted' | 'rejected' | 'rolled_back';
  createdAt: Date;
}

export interface LearnerRun {
  id: string;
  replayBatchId: string;
  policyVersionBefore: string;
  policyVersionAfter?: string;
  baslineMetricsJson: Record<string, number>;
  candidateCount: number;
  bestCandidateId?: string;
  status: 'in_progress' | 'completed' | 'failed';
  createdAt: Date;
}

export class LearnerService {
  /**
   * Load replay batch and create learner run
   */
  async startLearnerRun(replayBatchId: string, policyVersion: string = '1.0'): Promise<LearnerRun> {
    const learnerRunId = uuidv4();
    const now = new Date();

    // Verify replay batch exists
    const batchResult = await db.query(
      `SELECT id, batch_hash, trajectory_ids, batch_size FROM replay_batches WHERE id = $1`,
      [replayBatchId]
    );

    if (batchResult.rows.length === 0) {
      throw new Error(`Replay batch not found: ${replayBatchId}`);
    }

    const batch = batchResult.rows[0];
    const trajectoryIds = batch.trajectory_ids || [];

    // Verify all trajectories exist
    if (trajectoryIds.length > 0) {
      const trajResult = await db.query(
        `SELECT COUNT(*) as count FROM trajectory_store WHERE id = ANY($1)`,
        [trajectoryIds]
      );
      const foundCount = parseInt(trajResult.rows[0].count);
      if (foundCount !== trajectoryIds.length) {
        throw new Error(`Only ${foundCount}/${trajectoryIds.length} trajectories found in database`);
      }
    }

    // Compute baseline metrics from trajectories
    const metricsQuery = await db.query(
      `SELECT
        COUNT(*) as trajectory_count,
        AVG(reward) as avg_reward,
        MAX(reward) as max_reward,
        MIN(reward) as min_reward,
        STDDEV(reward) as stddev_reward
       FROM trajectory_store
       WHERE episode_id IN (
         SELECT DISTINCT episode_id FROM trajectory_store WHERE id = ANY($1)
       )`,
      [trajectoryIds]
    );

    const metrics = metricsQuery.rows[0];
    const baselineMetrics = {
      trajectory_count: parseInt(metrics.trajectory_count) || 0,
      avg_reward: parseFloat(metrics.avg_reward) || 0.5,
      max_reward: parseFloat(metrics.max_reward) || 1.0,
      min_reward: parseFloat(metrics.min_reward) || 0.0,
      stddev_reward: parseFloat(metrics.stddev_reward) || 0.1,
    };

    // Create learner run record
    const result = await db.query(
      `INSERT INTO learner_runs (
        id, replay_batch_id, policy_version_before, baseline_metrics_json, status, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id, created_at`,
      [
        learnerRunId,
        replayBatchId,
        policyVersion,
        JSON.stringify(baselineMetrics),
        'in_progress',
        now,
      ]
    );

    return {
      id: result.rows[0].id,
      replayBatchId,
      policyVersionBefore: policyVersion,
      baslineMetricsJson: baselineMetrics,
      candidateCount: 0,
      status: 'in_progress',
      createdAt: result.rows[0].created_at,
    };
  }

  /**
   * Generate a candidate artifact from replay batch
   * This is a simple heuristic: suggest a prompt update based on trajectories where reward was low
   */
  async generateCandidate(
    learnerRunId: string,
    candidateType: LearnerCandidate['candidateType'] = 'prompt_update'
  ): Promise<LearnerCandidate> {
    // Get learner run (with row-level lock to prevent concurrent modification)
    const runResult = await db.query(
      `SELECT id, replay_batch_id, baseline_metrics_json FROM learner_runs
       WHERE id = $1 FOR UPDATE`,
      [learnerRunId]
    );

    if (runResult.rows.length === 0) {
      throw new Error(`Learner run not found: ${learnerRunId}`);
    }

    const run = runResult.rows[0];
    const replayBatchId = run.replay_batch_id;
    const baselineMetrics = typeof run.baseline_metrics_json === 'string'
      ? JSON.parse(run.baseline_metrics_json)
      : run.baseline_metrics_json;

    // Get trajectories from replay batch (with row-level lock)
    const batchResult = await db.query(
      `SELECT trajectory_ids FROM replay_batches WHERE id = $1 FOR UPDATE`,
      [replayBatchId]
    );

    if (batchResult.rows.length === 0) {
      throw new Error(`Replay batch not found: ${replayBatchId}`);
    }

    const trajectoryIds = batchResult.rows[0].trajectory_ids || [];

    // Analyze low-reward trajectories
    let candidate: any = {
      type: candidateType,
      version: '1.1',
      rationale: 'Generated from replay batch analysis',
      changes: [],
    };

    if (candidateType === 'prompt_update') {
      // Simple heuristic: suggest more detailed instructions if avg reward is low
      if (baselineMetrics.avg_reward < 0.7) {
        candidate.changes.push({
          field: 'system_prompt',
          action: 'append_instruction',
          value: '\nImportant: Be more cautious and verify each step carefully.',
          reason: 'Low reward trajectories suggest need for more careful execution',
        });
      }
    } else if (candidateType === 'config_update') {
      // Suggest config changes based on variance
      if (baselineMetrics.stddev_reward > 0.3) {
        candidate.changes.push({
          field: 'execution_timeout',
          action: 'update',
          value: 15000,
          reason: 'High variance in rewards suggests need for longer timeouts',
        });
      }
    } else if (candidateType === 'heuristic_update') {
      // Suggest planning heuristic updates
      candidate.changes.push({
        field: 'step_validator',
        action: 'update_weights',
        value: { safety: 1.0, correctness: 0.9, efficiency: 0.7 },
        reason: 'Prioritize safety and correctness over efficiency',
      });
    } else if (candidateType === 'memory_policy_update') {
      // Suggest memory retrieval policy updates
      candidate.changes.push({
        field: 'memory_retrieval_threshold',
        action: 'update',
        value: 0.6,
        reason: 'Improve memory recall by lowering threshold slightly',
      });
    }

    // Create artifact
    const candidateJson = JSON.stringify(candidate);
    const artifactHash = crypto.createHash('sha256').update(candidateJson).digest('hex');

    // Store artifact
    const artifactId = uuidv4();
    const artifactResult = await db.query(
      `INSERT INTO artifacts (
        id, artifact_type, artifact_hash, artifact_json, lineage_json,
        is_simulation_derived, status, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
       RETURNING id`,
      [
        artifactId,
        candidateType,
        artifactHash,
        candidateJson,
        JSON.stringify({
          source: 'learner',
          learner_run_id: learnerRunId,
          replay_batch_id: replayBatchId,
          trajectory_count: trajectoryIds.length,
        }),
        false, // Not simulation-derived
        'created',
      ]
    );

    // Project simulated metrics after applying candidate (simple heuristic)
    const projectedMetrics = {
      trajectory_count: baselineMetrics.trajectory_count,
      avg_reward: Math.min(1.0, baselineMetrics.avg_reward * 1.1), // 10% improvement estimate
      max_reward: Math.min(1.0, baselineMetrics.max_reward * 1.05),
      min_reward: Math.max(0.0, baselineMetrics.min_reward * 0.95),
      stddev_reward: Math.max(0, baselineMetrics.stddev_reward * 0.9), // Reduce variance
    };

    const improvementPercent =
      ((projectedMetrics.avg_reward - baselineMetrics.avg_reward) / baselineMetrics.avg_reward) * 100;

    // Create learner candidate record
    const candidateId = uuidv4();
    const now = new Date();

    const candResult = await db.query(
      `INSERT INTO learner_candidates (
        id, learner_run_id, candidate_type, artifact_id, artifact_hash,
        metrics_before_json, metrics_after_json, improvement_percent,
        status, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id, created_at`,
      [
        candidateId,
        learnerRunId,
        candidateType,
        artifactId,
        artifactHash,
        JSON.stringify(baselineMetrics),
        JSON.stringify(projectedMetrics),
        improvementPercent,
        'created',
        now,
      ]
    );

    // Update learner run to track candidates
    await db.query(
      `UPDATE learner_runs SET best_candidate_id = $1 WHERE id = $2`,
      [candidateId, learnerRunId]
    );

    return {
      id: candResult.rows[0].id,
      learnerRunId,
      candidateType,
      artifactId,
      artifactHash,
      metricsBeforeJson: baselineMetrics,
      metricsAfterJson: projectedMetrics,
      improvementPercent,
      status: 'created',
      createdAt: candResult.rows[0].created_at,
    };
  }

  /**
   * Retrieve memory with stale demotion (rank by freshness first)
   * AREA 8: Memory Quality Hardening
   */
  async retrieveMemory(query: string, limit: number = 10): Promise<any[]> {
    const now = new Date();
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const oneMonthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    // Retrieve trajectories ranked by freshness, demoting stale ones
    const result = await db.query(
      `SELECT
        id, episode_id, reward, created_at,
        CASE
          WHEN created_at > $2 THEN 'fresh'
          WHEN created_at > $3 THEN 'recent'
          ELSE 'stale'
        END as freshness_category,
        CASE
          WHEN created_at > $2 THEN 3
          WHEN created_at > $3 THEN 2
          ELSE 1
        END as freshness_rank
       FROM trajectory_store
       ORDER BY freshness_rank DESC, reward DESC
       LIMIT $1`,
      [limit, oneWeekAgo, oneMonthAgo]
    );

    const trajectories = result.rows.map((row: any) => ({
      id: row.id,
      episodeId: row.episode_id,
      reward: parseFloat(row.reward),
      createdAt: row.created_at,
      freshnessCategory: row.freshness_category,
      warning: row.freshness_category === 'stale' ? 'Using stale memory (>30 days old)' : undefined,
    }));

    // Log warning if using stale memory
    const staleCount = trajectories.filter((t: any) => t.freshnessCategory === 'stale').length;
    if (staleCount > 0) {
      console.warn(`[MEMORY_QUALITY] Retrieved ${staleCount}/${trajectories.length} stale trajectories (>30 days old)`);
    }

    return trajectories;
  }

  /**
   * Create replay batch with simulation label enforcement
   * AREA 8: Replay Quality Hardening
   */
  async createReplayBatch(trajectoryIds: string[]): Promise<string> {
    if (trajectoryIds.length === 0) {
      throw new Error('Cannot create replay batch with no trajectories');
    }

    // Check simulation labels - must be consistent
    const labelResult = await db.query(
      `SELECT DISTINCT is_simulation FROM trajectory_store WHERE id = ANY($1)`,
      [trajectoryIds]
    );

    const labels = labelResult.rows.map((r: any) => r.is_simulation);
    if (labels.length > 1) {
      throw new Error(
        `Cannot mix simulation and real trajectories in replay batch. Found: ${labels.join(', ')}`
      );
    }

    const isSimulation = labels.length > 0 ? labels[0] : false;

    // Create batch hash
    const batchHash = crypto
      .createHash('sha256')
      .update(trajectoryIds.sort().join(','))
      .digest('hex');

    const batchId = uuidv4();
    const result = await db.query(
      `INSERT INTO replay_batches (
        id, batch_hash, trajectory_ids, batch_size, is_simulation, created_at
      ) VALUES ($1, $2, $3, $4, $5, NOW())
       RETURNING id`,
      [batchId, batchHash, trajectoryIds, trajectoryIds.length, isSimulation]
    );

    if (isSimulation) {
      console.warn(`[REPLAY_QUALITY] Created simulation batch ${batchId} (${trajectoryIds.length} trajectories)`);
    }

    return result.rows[0].id;
  }

  /**
   * Complete learner run
   */
  async completeLearnerRun(learnerRunId: string): Promise<void> {
    const result = await db.query(
      `UPDATE learner_runs
       SET status = 'completed'
       WHERE id = $1
       RETURNING id`,
      [learnerRunId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Learner run not found: ${learnerRunId}`);
    }
  }

  /**
   * Get learner run details
   */
  async getLearnerRun(learnerRunId: string): Promise<LearnerRun> {
    const result = await db.query(
      `SELECT id, replay_batch_id, policy_version_before, baseline_metrics_json,
              best_candidate_id, status, created_at
       FROM learner_runs WHERE id = $1`,
      [learnerRunId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Learner run not found: ${learnerRunId}`);
    }

    const row = result.rows[0];
    return {
      id: row.id,
      replayBatchId: row.replay_batch_id,
      policyVersionBefore: row.policy_version_before,
      bestCandidateId: row.best_candidate_id,
      baslineMetricsJson: JSON.parse(row.baseline_metrics_json),
      candidateCount: 1, // Simplified
      status: row.status,
      createdAt: row.created_at,
    };
  }

  /**
   * Get candidate by ID
   */
  async getCandidate(candidateId: string): Promise<LearnerCandidate> {
    const result = await db.query(
      `SELECT id, learner_run_id, candidate_type, artifact_id, artifact_hash,
              metrics_before_json, metrics_after_json, improvement_percent,
              status, created_at
       FROM learner_candidates WHERE id = $1`,
      [candidateId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Candidate not found: ${candidateId}`);
    }

    const row = result.rows[0];
    return {
      id: row.id,
      learnerRunId: row.learner_run_id,
      candidateType: row.candidate_type,
      artifactId: row.artifact_id,
      artifactHash: row.artifact_hash,
      metricsBeforeJson: JSON.parse(row.metrics_before_json),
      metricsAfterJson: JSON.parse(row.metrics_after_json),
      improvementPercent: parseFloat(row.improvement_percent),
      status: row.status,
      createdAt: row.created_at,
    };
  }

  /**
   * Update candidate status (called by eval harness)
   */
  async updateCandidateStatus(
    candidateId: string,
    status: LearnerCandidate['status']
  ): Promise<void> {
    const result = await db.query(
      `UPDATE learner_candidates SET status = $1 WHERE id = $2 RETURNING id`,
      [status, candidateId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Candidate not found: ${candidateId}`);
    }
  }
}

// Export singleton instance
export const learner = new LearnerService();
