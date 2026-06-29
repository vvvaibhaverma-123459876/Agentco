import { db } from '../db/client';

export type FailureType =
  | 'timeout'
  | 'max_retries_exceeded'
  | 'fatal_error'
  | 'invalid_state'
  | 'dependency_failure'
  | 'resource_exhaustion'
  | 'policy_violation'
  | 'human_cancelled';

export interface Checkpoint {
  id: string;
  taskId: string;
  stepName: string;
  stepIndex: number;
  stateJson: Record<string, any>;
  artifactRefsJson: string[];
  retryCount: number;
  traceId?: string;
  createdAt: Date;
}

export interface FailureLineage {
  taskId: string;
  failureType: FailureType;
  errorMessage: string;
  errorCode?: string;
  stackTrace?: string;
  checkpointIndex: number;
  attemptCount: number;
  retryEligible: boolean;
}

/**
 * Crash Recovery Service
 *
 * Handles task resumption after failures by:
 * 1. Saving checkpoints at each step
 * 2. Detecting and expiring stale worker leases
 * 3. Resuming from the last successful checkpoint
 * 4. Classifying failures (retryable vs terminal)
 * 5. Implementing exponential backoff retry logic
 * 6. Tracking failure lineage for debugging
 */
export class CrashRecoveryService {
  private readonly MAX_RETRIES = 5;
  private readonly INITIAL_RETRY_DELAY_MS = 1000; // 1 second
  private readonly MAX_RETRY_DELAY_MS = 32000; // 32 seconds

  /**
   * Save checkpoint at current step for future resumption
   */
  async saveCheckpoint(
    taskId: string,
    stepIndex: number,
    stepName: string,
    state: Record<string, any>,
    traceId?: string
  ): Promise<string> {
    const result = await db.query(
      `INSERT INTO autonomy_workflow_checkpoints (
        task_id, step_index, step_name, state_json, trace_id, retry_count
      ) VALUES ($1, $2, $3, $4, $5, 0)
       ON CONFLICT (task_id, step_index) DO UPDATE
       SET state_json = EXCLUDED.state_json, trace_id = EXCLUDED.trace_id
       RETURNING id`,
      [taskId, stepIndex, stepName, JSON.stringify(state), traceId]
    );

    if (result.rows.length === 0) {
      throw new Error('Failed to save checkpoint');
    }

    return result.rows[0].id;
  }

  /**
   * Get the last successful checkpoint for a task
   */
  async getLastCheckpoint(taskId: string): Promise<Checkpoint | null> {
    const result = await db.query(
      `SELECT id, task_id, step_name, step_index, state_json,
              artifact_refs_json, retry_count, trace_id, created_at
       FROM autonomy_workflow_checkpoints
       WHERE task_id = $1
       ORDER BY step_index DESC
       LIMIT 1`,
      [taskId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      taskId: row.task_id,
      stepName: row.step_name,
      stepIndex: row.step_index,
      stateJson: row.state_json,
      artifactRefsJson: row.artifact_refs_json || [],
      retryCount: row.retry_count,
      traceId: row.trace_id,
      createdAt: row.created_at,
    };
  }

  /**
   * Get a specific checkpoint
   */
  async getCheckpoint(taskId: string, stepIndex: number): Promise<Checkpoint | null> {
    const result = await db.query(
      `SELECT id, task_id, step_name, step_index, state_json,
              artifact_refs_json, retry_count, trace_id, created_at
       FROM autonomy_workflow_checkpoints
       WHERE task_id = $1 AND step_index = $2
       LIMIT 1`,
      [taskId, stepIndex]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      taskId: row.task_id,
      stepName: row.step_name,
      stepIndex: row.step_index,
      stateJson: row.state_json,
      artifactRefsJson: row.artifact_refs_json || [],
      retryCount: row.retry_count,
      traceId: row.trace_id,
      createdAt: row.created_at,
    };
  }

  /**
   * Increment retry count for a checkpoint
   */
  async incrementCheckpointRetry(taskId: string, stepIndex: number): Promise<number> {
    const result = await db.query(
      `UPDATE autonomy_workflow_checkpoints
       SET retry_count = retry_count + 1
       WHERE task_id = $1 AND step_index = $2
       RETURNING retry_count`,
      [taskId, stepIndex]
    );

    if (result.rows.length === 0) {
      throw new Error(`Checkpoint not found for task ${taskId} step ${stepIndex}`);
    }

    return result.rows[0].retry_count;
  }

  /**
   * Classify an error as retryable or terminal
   */
  classifyError(error: any): { type: FailureType; retryable: boolean; delay: number } {
    const message = error.message?.toLowerCase() || '';
    const code = error.code || '';

    // Timeout errors are retryable
    if (message.includes('timeout') || code === 'ETIMEDOUT') {
      return { type: 'timeout', retryable: true, delay: 2000 };
    }

    // Connection errors are retryable
    if (message.includes('connection') || code === 'ECONNREFUSED' || code === 'ECONNRESET') {
      return { type: 'dependency_failure', retryable: true, delay: 3000 };
    }

    // Resource exhaustion is retryable
    if (message.includes('resource') || message.includes('memory') || message.includes('lock')) {
      return { type: 'resource_exhaustion', retryable: true, delay: 5000 };
    }

    // Validation/state errors are NOT retryable
    if (message.includes('invalid') || message.includes('constraint') || message.includes('state')) {
      return { type: 'invalid_state', retryable: false, delay: 0 };
    }

    // Policy violations are NOT retryable
    if (message.includes('policy') || message.includes('permission') || message.includes('forbidden')) {
      return { type: 'policy_violation', retryable: false, delay: 0 };
    }

    // Everything else is a fatal error
    return { type: 'fatal_error', retryable: false, delay: 0 };
  }

  /**
   * Record a failure in the dead-letter queue
   */
  async recordFailure(
    taskId: string,
    failureType: FailureType,
    error: any,
    checkpointIndex: number,
    attemptCount: number,
    lastState?: Record<string, any>
  ): Promise<void> {
    await db.query(
      `INSERT INTO autonomy_dead_letters (
        task_id, failure_type, error_message, error_code, stack_trace,
        last_state, attempts, requeue_eligible, payload_json
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
      [
        taskId,
        failureType,
        error.message || 'Unknown error',
        error.code || null,
        error.stack || null,
        lastState ? JSON.stringify(lastState) : null,
        attemptCount,
        ['timeout', 'dependency_failure', 'resource_exhaustion'].includes(failureType),
        JSON.stringify({ checkpointIndex, failureType }),
      ]
    );
  }

  /**
   * Calculate exponential backoff delay
   */
  calculateBackoffDelay(attemptNumber: number): number {
    // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s
    const baseDelay = Math.min(
      this.INITIAL_RETRY_DELAY_MS * Math.pow(2, attemptNumber - 1),
      this.MAX_RETRY_DELAY_MS
    );

    // Add jitter (±10%)
    const jitter = baseDelay * 0.1 * (Math.random() * 2 - 1);
    return Math.max(0, Math.round(baseDelay + jitter));
  }

  /**
   * Determine if an error is retryable and get retry delay
   */
  shouldRetry(error: any, attemptCount: number): { shouldRetry: boolean; delay: number } {
    const classification = this.classifyError(error);

    if (!classification.retryable) {
      return { shouldRetry: false, delay: 0 };
    }

    if (attemptCount >= this.MAX_RETRIES) {
      return { shouldRetry: false, delay: 0 };
    }

    const delay = this.calculateBackoffDelay(attemptCount + 1);
    return { shouldRetry: true, delay };
  }

  /**
   * Detect and release expired worker leases
   * Call this periodically to clean up stale leases from crashed workers
   */
  async detectExpiredWorkerLeases(): Promise<number> {
    const result = await db.query(
      `UPDATE worker_leases
       SET status = 'expired'
       WHERE status = 'active' AND lease_expires_at < NOW()
       RETURNING id`
    );

    const expiredCount = result.rows.length;
    if (expiredCount > 0) {
      console.log(`[CRASH_RECOVERY] Released ${expiredCount} expired worker leases`);
    }
    return expiredCount;
  }

  /**
   * Requeue a dead-lettered task if eligible
   */
  async requeueDeadLetteredTask(taskId: string, reason: string): Promise<boolean> {
    // Check if task is eligible for requeue
    const deadLetterResult = await db.query(
      `SELECT requeue_eligible FROM autonomy_dead_letters
       WHERE task_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [taskId]
    );

    if (deadLetterResult.rows.length === 0 || !deadLetterResult.rows[0].requeue_eligible) {
      return false;
    }

    // Update the dead letter to mark as requeued
    await db.query(
      `UPDATE autonomy_dead_letters
       SET requeue_reason = $1, archived_at = NOW()
       WHERE task_id = $2`,
      [reason, taskId]
    );

    // Reset task to created status for retry
    await db.query(
      `UPDATE autonomy_tasks
       SET status = 'created'
       WHERE id = $1`,
      [taskId]
    );

    console.log(`[CRASH_RECOVERY] Requeued dead-lettered task ${taskId}: ${reason}`);
    return true;
  }
}

// Export singleton instance
export const crashRecovery = new CrashRecoveryService();
