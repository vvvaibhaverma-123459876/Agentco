import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface Episode {
  id: string;
  taskId?: string;
  runId: string;
  agentId: string;
  title: string;
  domain: string;
  riskLevel: string;
  autonomyLevel: number;
  outcomeStatus?: string;
  rewardScore?: number;
  regretScore?: number;
  interventionRequired: boolean;
  createdAt: Date;
}

export interface Action {
  id: string;
  episodeId: string;
  stepIndex: number;
  actionType: string;
  toolName?: string;
  success: boolean;
  createdAt: Date;
}

export interface TrajectoryStep {
  id: string;
  episodeId: string;
  stepIndex: number;
  state: Record<string, any>;
  action: Record<string, any>;
  observation: Record<string, any>;
  reward: number;
  done: boolean;
}

export interface ReplayBatch {
  id: string;
  trajectoryIds: string[];
  batchHash: string;
  created: Date;
}

export class TrajectoryStoreService {
  /**
   * Create a new episode
   */
  async createEpisode(episode: Omit<Episode, 'id' | 'createdAt'>): Promise<Episode> {
    const id = uuidv4();
    const now = new Date();

    const result = await db.query(
      `INSERT INTO autonomy_episodes (
        id, task_id, run_id, agent_id, title, domain, risk_level, autonomy_level,
        intervention_required, trace_id, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
       RETURNING id, created_at`,
      [
        id,
        episode.taskId,
        episode.runId,
        episode.agentId,
        episode.title,
        episode.domain,
        episode.riskLevel,
        episode.autonomyLevel,
        episode.interventionRequired,
        uuidv4(), // trace_id
        now,
      ]
    );

    return {
      ...episode,
      id: result.rows[0].id,
      createdAt: result.rows[0].created_at,
    };
  }

  /**
   * Record action in episode
   */
  async recordAction(episodeId: string, stepIndex: number, action: Omit<Action, 'id' | 'episodeId' | 'stepIndex' | 'createdAt'>): Promise<Action> {
    const id = uuidv4();
    const now = new Date();

    const result = await db.query(
      `INSERT INTO autonomy_actions (
        id, episode_id, step_index, action_type, tool_name, success, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id, created_at`,
      [
        id,
        episodeId,
        stepIndex,
        action.actionType,
        action.toolName,
        action.success,
        now,
      ]
    );

    return {
      id: result.rows[0].id,
      episodeId,
      stepIndex,
      ...action,
      createdAt: result.rows[0].created_at,
    };
  }

  /**
   * Record outcome for episode
   */
  async recordOutcome(episodeId: string, outcome: {
    outcomeType: string;
    outcomeStatus: string;
    objectiveResult?: Record<string, any>;
  }): Promise<void> {
    const id = uuidv4();

    await db.query(
      `INSERT INTO autonomy_outcomes (
        id, episode_id, outcome_type, outcome_status, objective_result_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, now())`,
      [
        id,
        episodeId,
        outcome.outcomeType,
        outcome.outcomeStatus,
        JSON.stringify(outcome.objectiveResult ?? {}),
      ]
    );

    // Update episode with outcome
    await db.query(
      `UPDATE autonomy_episodes SET outcome_status = $2, ended_at = now() WHERE id = $1`,
      [episodeId, outcome.outcomeStatus]
    );
  }

  /**
   * Store trajectory step (state-action-observation-reward)
   */
  async recordTrajectoryStep(
    episodeId: string,
    stepIndex: number,
    trajectory: Omit<TrajectoryStep, 'id' | 'episodeId' | 'stepIndex'>
  ): Promise<TrajectoryStep> {
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO trajectory_store (
        id, episode_id, step_index, state_json, action_json, observation_json, reward, done, created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, now())
       RETURNING id`,
      [
        id,
        episodeId,
        stepIndex,
        JSON.stringify(trajectory.state),
        JSON.stringify(trajectory.action),
        JSON.stringify(trajectory.observation),
        trajectory.reward,
        trajectory.done,
      ]
    );

    return {
      id: result.rows[0].id,
      episodeId,
      stepIndex,
      ...trajectory,
    };
  }

  /**
   * Create replay batch from trajectories
   */
  async createReplayBatch(
    trajectoryIds: string[],
    sourceFilter: Record<string, any> = {}
  ): Promise<ReplayBatch> {
    const id = uuidv4();

    // Compute batch hash from sorted trajectory IDs (deterministic)
    const sortedIds = [...trajectoryIds].sort();
    const crypto = await import('crypto');
    const hash = crypto
      .createHash('sha256')
      .update(JSON.stringify(sortedIds))
      .digest('hex');

    // Check if batch with this hash already exists
    const existing = await db.query(
      `SELECT id FROM replay_batches WHERE batch_hash = $1`,
      [hash]
    );

    if (existing.rows.length > 0) {
      return {
        id: existing.rows[0].id,
        trajectoryIds,
        batchHash: hash,
        created: new Date(),
      };
    }

    // Create new batch
    const result = await db.query(
      `INSERT INTO replay_batches (
        id, batch_hash, trajectory_ids, batch_size, source_filter_json, created_at
      ) VALUES ($1, $2, $3, $4, $5, now())
       RETURNING id, created_at`,
      [id, hash, trajectoryIds, trajectoryIds.length, JSON.stringify(sourceFilter)]
    );

    return {
      id: result.rows[0].id,
      trajectoryIds,
      batchHash: hash,
      created: result.rows[0].created_at,
    };
  }

  /**
   * Get trajectories for learning
   */
  async getTrajectories(
    filters: {
      agentId?: string;
      domain?: string;
      minReward?: number;
      maxRegret?: number;
      limit?: number;
    } = {}
  ): Promise<TrajectoryStep[]> {
    let query = `SELECT t.id, t.episode_id, t.step_index, t.state_json, t.action_json, t.observation_json, t.reward, t.done
                  FROM trajectory_store t
                  JOIN autonomy_episodes e ON t.episode_id = e.id
                  WHERE 1=1`;
    const params: any[] = [];

    if (filters.agentId) {
      params.push(filters.agentId);
      query += ` AND e.agent_id = $${params.length}`;
    }

    if (filters.domain) {
      params.push(filters.domain);
      query += ` AND e.domain = $${params.length}`;
    }

    if (filters.minReward !== undefined) {
      params.push(filters.minReward);
      query += ` AND t.reward >= $${params.length}`;
    }

    if (filters.maxRegret !== undefined) {
      params.push(filters.maxRegret);
      query += ` AND e.regret_score <= $${params.length}`;
    }

    query += ` ORDER BY t.created_at DESC`;

    if (filters.limit) {
      params.push(filters.limit);
      query += ` LIMIT $${params.length}`;
    }

    const result = await db.query(query, params);

    return result.rows.map((row: any) => ({
      id: row.id,
      episodeId: row.episode_id,
      stepIndex: row.step_index,
      state: row.state_json,
      action: row.action_json,
      observation: row.observation_json,
      reward: row.reward,
      done: row.done,
    }));
  }

  /**
   * Get episode by ID
   */
  async getEpisode(episodeId: string): Promise<Episode | null> {
    const result = await db.query(
      `SELECT id, task_id, run_id, agent_id, title, domain, risk_level, autonomy_level,
              outcome_status, reward_score, regret_score, intervention_required, created_at
       FROM autonomy_episodes WHERE id = $1`,
      [episodeId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      taskId: row.task_id,
      runId: row.run_id,
      agentId: row.agent_id,
      title: row.title,
      domain: row.domain,
      riskLevel: row.risk_level,
      autonomyLevel: row.autonomy_level,
      outcomeStatus: row.outcome_status,
      rewardScore: row.reward_score,
      regretScore: row.regret_score,
      interventionRequired: row.intervention_required,
      createdAt: row.created_at,
    };
  }

  /**
   * Mark episode with regret score
   */
  async markRegret(episodeId: string, regretScore: number): Promise<void> {
    await db.query(
      `UPDATE autonomy_episodes SET regret_score = $2 WHERE id = $1`,
      [episodeId, regretScore]
    );
  }

  /**
   * Record intervention
   */
  async recordIntervention(
    episodeId: string,
    interventionType: string,
    actor: string,
    reason: string,
    severity: string = 'info'
  ): Promise<void> {
    await db.query(
      `INSERT INTO autonomy_interventions (id, episode_id, intervention_type, intervention_actor, reason, severity, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, now())`,
      [
        uuidv4(),
        episodeId,
        interventionType,
        actor,
        reason,
        severity,
      ]
    );

    // Update episode intervention count
    await db.query(
      `UPDATE autonomy_episodes
       SET intervention_count = intervention_count + 1, intervention_required = true
       WHERE id = $1`,
      [episodeId]
    );
  }

  /**
   * Get high-regret episodes for analysis
   */
  async getHighRegretEpisodes(threshold: number = 0.5, limit: number = 10): Promise<Episode[]> {
    const result = await db.query(
      `SELECT id, task_id, run_id, agent_id, title, domain, risk_level, autonomy_level,
              outcome_status, reward_score, regret_score, intervention_required, created_at
       FROM autonomy_episodes
       WHERE regret_score >= $1
       ORDER BY regret_score DESC
       LIMIT $2`,
      [threshold, limit]
    );

    return result.rows.map((row: any) => ({
      id: row.id,
      taskId: row.task_id,
      runId: row.run_id,
      agentId: row.agent_id,
      title: row.title,
      domain: row.domain,
      riskLevel: row.risk_level,
      autonomyLevel: row.autonomy_level,
      outcomeStatus: row.outcome_status,
      rewardScore: row.reward_score,
      regretScore: row.regret_score,
      interventionRequired: row.intervention_required,
      createdAt: row.created_at,
    }));
  }
}

export const trajectoryStore = new TrajectoryStoreService();
