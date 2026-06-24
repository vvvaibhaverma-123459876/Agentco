import { db } from '../db/client';
import { v4 as uuidv4 } from 'uuid';

export interface TaskCreationInput {
  taskType: string;
  title: string;
  description?: string;
  source: 'system' | 'agent' | 'user' | 'simulator';
  sourceId?: string;
  createdBy: string;
  assignedAgentId?: string;
  assignedInstitutionId?: string;
  priority?: number;
  riskLevel?: string;
  autonomyLevel?: number;
  parentTaskId?: string;
  traceId?: string;
  runId?: string;
  idempotencyKey?: string;
  timeout?: number;
  payload?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface Task {
  id: string;
  taskType: string;
  title: string;
  status: string;
  traceId?: string;
  runId?: string;
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  failedAt?: Date;
}

export class TaskEngineService {
  /**
   * Create a new autonomy task with idempotency guarantee
   */
  async createTask(input: TaskCreationInput): Promise<Task> {
    // Check idempotency
    if (input.idempotencyKey) {
      const existing = await db.query(
        `SELECT id, status, created_at FROM autonomy_tasks
         WHERE idempotency_key = $1 AND status NOT IN ('cancelled', 'dead_lettered')`,
        [input.idempotencyKey]
      );

      if (existing.rows.length > 0) {
        const row = existing.rows[0];
        return {
          id: row.id,
          taskType: input.taskType,
          title: input.title,
          status: row.status,
          createdAt: row.created_at,
        };
      }
    }

    // Create new task
    const taskId = uuidv4();
    const now = new Date();

    const result = await db.query(
      `INSERT INTO autonomy_tasks (
        id, task_type, title, description, source, source_id,
        created_by, assigned_agent_id, assigned_institution_id,
        priority, risk_level, autonomy_level, parent_task_id,
        trace_id, run_id, idempotency_key, status,
        timeout_at, payload, metadata, created_at, updated_at
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13,
        $14, $15, $16, 'created', $17, $18, $19, $20, $21
      ) RETURNING id, status, created_at`,
      [
        taskId,
        input.taskType,
        input.title,
        input.description,
        input.source,
        input.sourceId,
        input.createdBy,
        input.assignedAgentId,
        input.assignedInstitutionId,
        input.priority ?? 50,
        input.riskLevel ?? 'low',
        input.autonomyLevel ?? 0,
        input.parentTaskId,
        input.traceId,
        input.runId,
        input.idempotencyKey,
        input.timeout ? new Date(Date.now() + input.timeout * 1000) : null,
        input.payload ?? {},
        input.metadata ?? {},
        now,
        now,
      ]
    );

    const row = result.rows[0];
    return {
      id: row.id,
      taskType: input.taskType,
      title: input.title,
      status: row.status,
      traceId: input.traceId,
      runId: input.runId,
      createdAt: row.created_at,
    };
  }

  /**
   * Queue a task (created → queued)
   */
  async queueTask(taskId: string): Promise<void> {
    await db.query(
      `UPDATE autonomy_tasks SET status = 'queued' WHERE id = $1`,
      [taskId]
    );
  }

  /**
   * Claim a task and get a worker lease (queued → leased)
   */
  async leaseTask(taskId: string, workerId: string, leaseSeconds: number = 300): Promise<string> {
    const leaseExpires = new Date(Date.now() + leaseSeconds * 1000);

    // Atomically lease task
    const result = await db.query(
      `UPDATE autonomy_tasks SET status = 'leased' WHERE id = $1 AND status = 'queued'
       RETURNING id`,
      [taskId]
    );

    if (result.rows.length === 0) {
      throw new Error(`Task ${taskId} is not in queued state`);
    }

    // Create worker lease
    const leaseId = uuidv4();
    await db.query(
      `INSERT INTO worker_leases (id, task_id, worker_id, lease_expires_at, status)
       VALUES ($1, $2, $3, $4, 'active')`,
      [leaseId, taskId, workerId, leaseExpires]
    );

    return leaseId;
  }

  /**
   * Start executing task (leased → running)
   */
  async startTask(taskId: string): Promise<void> {
    const now = new Date();
    await db.query(
      `UPDATE autonomy_tasks SET status = 'running', started_at = $2 WHERE id = $1`,
      [taskId, now]
    );
  }

  /**
   * Wait for external resource (running → waiting_for_X)
   */
  async waitForResource(taskId: string, resourceType: 'tool' | 'memory' | 'human' | 'evaluation'): Promise<void> {
    const waitingStatus = `waiting_for_${resourceType.toUpperCase()}`;
    await db.query(
      `UPDATE autonomy_tasks SET status = $2 WHERE id = $1`,
      [taskId, waitingStatus]
    );
  }

  /**
   * Resume from waiting state
   */
  async resumeTask(taskId: string): Promise<void> {
    await db.query(
      `UPDATE autonomy_tasks SET status = 'running' WHERE id = $1 AND status LIKE 'waiting_for_%'`,
      [taskId]
    );
  }

  /**
   * Complete task successfully
   */
  async completeTask(taskId: string, result?: Record<string, any>): Promise<void> {
    const now = new Date();
    await db.query(
      `UPDATE autonomy_tasks SET status = 'completed', completed_at = $2, result = $3 WHERE id = $1`,
      [taskId, now, JSON.stringify(result ?? {})]
    );
  }

  /**
   * Mark task as failed
   */
  async failTask(taskId: string, error: string, errorStack?: string, shouldRetry: boolean = true): Promise<void> {
    const now = new Date();

    // Get current retry count
    const task = await db.query(`SELECT retry_count, max_retries FROM autonomy_tasks WHERE id = $1`, [taskId]);
    if (task.rows.length === 0) {
      throw new Error(`Task ${taskId} not found`);
    }

    const retryCount = task.rows[0].retry_count;
    const maxRetries = task.rows[0].max_retries;

    if (shouldRetry && retryCount < maxRetries) {
      // Retry: go back to queued
      await db.query(
        `UPDATE autonomy_tasks SET status = 'queued', retry_count = $2, last_error = $3, last_error_stack = $4
         WHERE id = $1`,
        [taskId, retryCount + 1, error, errorStack]
      );
    } else {
      // Permanent failure
      await db.query(
        `UPDATE autonomy_tasks SET status = 'failed', failed_at = $2, last_error = $3, last_error_stack = $4
         WHERE id = $1`,
        [taskId, now, error, errorStack]
      );

      // Create dead letter entry
      await db.query(
        `INSERT INTO autonomy_dead_letters (task_id, failure_type, error_message, stack_trace, attempts)
         VALUES ($1, $2, $3, $4, $5)`,
        [taskId, 'max_retries_exceeded', error, errorStack, retryCount + 1]
      );
    }
  }

  /**
   * Cancel task
   */
  async cancelTask(taskId: string, reason?: string): Promise<void> {
    const now = new Date();
    await db.query(
      `UPDATE autonomy_tasks SET status = 'cancelled', cancelled_at = $2, metadata = jsonb_set(metadata, '{cancellation_reason}', $3)
       WHERE id = $1`,
      [taskId, now, JSON.stringify(reason ?? 'User cancelled')]
    );
  }

  /**
   * Get task by ID
   */
  async getTask(taskId: string): Promise<Task | null> {
    const result = await db.query(
      `SELECT id, task_type, title, status, trace_id, run_id, created_at, started_at, completed_at, failed_at
       FROM autonomy_tasks WHERE id = $1`,
      [taskId]
    );

    if (result.rows.length === 0) {
      return null;
    }

    const row = result.rows[0];
    return {
      id: row.id,
      taskType: row.task_type,
      title: row.title,
      status: row.status,
      traceId: row.trace_id,
      runId: row.run_id,
      createdAt: row.created_at,
      startedAt: row.started_at,
      completedAt: row.completed_at,
      failedAt: row.failed_at,
    };
  }

  /**
   * Save checkpoint for task
   */
  async saveCheckpoint(taskId: string, stepName: string, stepIndex: number, state: Record<string, any>, traceId?: string): Promise<void> {
    const checkpointId = uuidv4();
    await db.query(
      `INSERT INTO autonomy_workflow_checkpoints (id, task_id, step_name, step_index, state_json, trace_id)
       VALUES ($1, $2, $3, $4, $5, $6)
       ON CONFLICT (task_id, step_index) DO UPDATE SET state_json = $5, trace_id = $6`,
      [checkpointId, taskId, stepName, stepIndex, JSON.stringify(state), traceId]
    );
  }

  /**
   * Load checkpoint for task
   */
  async loadCheckpoint(taskId: string, stepIndex: number): Promise<Record<string, any> | null> {
    const result = await db.query(
      `SELECT state_json FROM autonomy_workflow_checkpoints WHERE task_id = $1 AND step_index = $2`,
      [taskId, stepIndex]
    );

    if (result.rows.length === 0) {
      return null;
    }

    return result.rows[0].state_json;
  }

  /**
   * Heartbeat: keep worker lease alive
   */
  async heartbeat(leaseId: string): Promise<void> {
    const now = new Date();
    await db.query(
      `UPDATE worker_leases SET last_heartbeat_at = $2 WHERE id = $1`,
      [leaseId, now]
    );
  }

  /**
   * Release lease
   */
  async releaseLease(leaseId: string): Promise<void> {
    await db.query(
      `UPDATE worker_leases SET status = 'released' WHERE id = $1`,
      [leaseId]
    );
  }

  /**
   * Check for expired leases and move tasks back to queued
   */
  async recoverExpiredLeases(): Promise<number> {
    const result = await db.query(
      `WITH expired AS (
         SELECT task_id FROM worker_leases WHERE status = 'active' AND lease_expires_at < now()
       )
       UPDATE autonomy_tasks SET status = 'queued'
       WHERE id IN (SELECT task_id FROM expired)
       RETURNING id`
    );

    return result.rowCount ?? 0;
  }

  /**
   * Check for timed-out tasks and move to failed
   */
  async recoverTimedOutTasks(): Promise<number> {
    const result = await db.query(
      `UPDATE autonomy_tasks SET status = 'failed', last_error = 'Task timeout exceeded'
       WHERE status IN ('running', 'waiting_for_tool', 'waiting_for_memory', 'waiting_for_human', 'waiting_for_evaluation')
       AND timeout_at < now()
       RETURNING id`
    );

    return result.rowCount ?? 0;
  }
}

export const taskEngine = new TaskEngineService();
