import crypto from 'crypto';
import { query } from '../db/client';

export type AgentTaskStatus =
  | 'queued'
  | 'leased'
  | 'running'
  | 'succeeded'
  | 'failed'
  | 'cancelled'
  | 'dead_letter';

export interface AgentTask {
  task_id: string;
  agent_id: string;
  task_type: string;
  payload: Record<string, unknown>;
  status: AgentTaskStatus;
  queued_at: string;
  leased_at?: string | null;
  lease_owner?: string | null;
  lease_expires_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
  retry_count: number;
  max_retries: number;
  correlation_id?: string | null;
  audit_event_id?: string | null;
}

function parseTask(row: Record<string, unknown>): AgentTask {
  return {
    task_id: String(row.task_id),
    agent_id: String(row.agent_id),
    task_type: String(row.task_type),
    payload: (row.payload ?? {}) as Record<string, unknown>,
    status: row.status as AgentTaskStatus,
    queued_at: String(row.queued_at),
    leased_at: row.leased_at ? String(row.leased_at) : null,
    lease_owner: row.lease_owner ? String(row.lease_owner) : null,
    lease_expires_at: row.lease_expires_at ? String(row.lease_expires_at) : null,
    started_at: row.started_at ? String(row.started_at) : null,
    completed_at: row.completed_at ? String(row.completed_at) : null,
    result: (row.result ?? null) as Record<string, unknown> | null,
    error: row.error ? String(row.error) : null,
    retry_count: Number(row.retry_count),
    max_retries: Number(row.max_retries),
    correlation_id: row.correlation_id ? String(row.correlation_id) : null,
    audit_event_id: row.audit_event_id ? String(row.audit_event_id) : null,
  };
}

export async function appendTaskEvent(
  taskId: string,
  eventType: string,
  payload: Record<string, unknown> = {},
): Promise<string> {
  const id = crypto.randomUUID();
  await query(
    `INSERT INTO agent_task_events (id, task_id, event_type, payload)
     VALUES ($1, $2, $3, $4::jsonb)`,
    [id, taskId, eventType, JSON.stringify(payload)],
  );
  return id;
}

export async function createTask(
  agentId: string,
  taskType: string,
  payload: Record<string, unknown> = {},
  options: { correlationId?: string; maxRetries?: number } = {},
): Promise<AgentTask> {
  const taskId = crypto.randomUUID();
  const rows = await query(
    `INSERT INTO agent_tasks
        (task_id, agent_id, task_type, payload, status, correlation_id, max_retries)
     VALUES ($1, $2, $3, $4::jsonb, 'queued', $5, $6)
     RETURNING *`,
    [taskId, agentId, taskType, JSON.stringify(payload), options.correlationId ?? taskId, options.maxRetries ?? 3],
  );
  await appendTaskEvent(taskId, 'task_queued', { agent_id: agentId, task_type: taskType });
  return parseTask(rows[0]);
}

export async function getTask(taskId: string): Promise<AgentTask | null> {
  const rows = await query(`SELECT * FROM agent_tasks WHERE task_id = $1`, [taskId]);
  return rows[0] ? parseTask(rows[0]) : null;
}

export async function listTasks(filters: { agentId?: string; status?: string } = {}): Promise<AgentTask[]> {
  const clauses: string[] = [];
  const params: unknown[] = [];
  if (filters.agentId) {
    params.push(filters.agentId);
    clauses.push(`agent_id = $${params.length}`);
  }
  if (filters.status) {
    params.push(filters.status);
    clauses.push(`status = $${params.length}`);
  }
  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
  const rows = await query(`SELECT * FROM agent_tasks ${where} ORDER BY queued_at DESC LIMIT 200`, params);
  return rows.map(parseTask);
}

export async function cancelTask(taskId: string): Promise<AgentTask | null> {
  const rows = await query(
    `UPDATE agent_tasks
        SET status = 'cancelled', completed_at = NOW()
      WHERE task_id = $1
        AND status IN ('queued', 'leased')
      RETURNING *`,
    [taskId],
  );
  if (!rows[0]) return null;
  await appendTaskEvent(taskId, 'task_cancelled');
  return parseTask(rows[0]);
}

export async function leaseOneTask(
  leaseOwner: string,
  leaseSeconds = 60,
): Promise<AgentTask | null> {
  const rows = await query(
    `WITH candidate AS (
       SELECT task_id
         FROM agent_tasks
        WHERE status = 'queued'
           OR (status = 'leased' AND lease_expires_at < NOW())
        ORDER BY queued_at
        LIMIT 1
        FOR UPDATE SKIP LOCKED
     )
     UPDATE agent_tasks t
        SET status = 'leased',
            leased_at = NOW(),
            lease_owner = $1,
            lease_expires_at = NOW() + ($2::text || ' seconds')::interval
       FROM candidate
      WHERE t.task_id = candidate.task_id
      RETURNING t.*`,
    [leaseOwner, leaseSeconds],
  );
  if (!rows[0]) return null;
  const task = parseTask(rows[0]);
  await appendTaskEvent(task.task_id, 'task_leased', { lease_owner: leaseOwner });
  return task;
}

export async function markTaskRunning(taskId: string): Promise<AgentTask | null> {
  const rows = await query(
    `UPDATE agent_tasks
        SET status = 'running', started_at = COALESCE(started_at, NOW())
      WHERE task_id = $1 AND status = 'leased'
      RETURNING *`,
    [taskId],
  );
  return rows[0] ? parseTask(rows[0]) : null;
}

export async function completeTask(
  taskId: string,
  result: Record<string, unknown>,
  auditEventId?: string,
): Promise<AgentTask | null> {
  const rows = await query(
    `UPDATE agent_tasks
        SET status = 'succeeded',
            completed_at = NOW(),
            result = $2::jsonb,
            audit_event_id = $3
      WHERE task_id = $1
      RETURNING *`,
    [taskId, JSON.stringify(result), auditEventId ?? null],
  );
  if (!rows[0]) return null;
  await appendTaskEvent(taskId, 'task_succeeded', { audit_event_id: auditEventId ?? null });
  return parseTask(rows[0]);
}

export async function failTask(taskId: string, error: string): Promise<AgentTask | null> {
  const rows = await query(
    `UPDATE agent_tasks
        SET status = CASE WHEN retry_count + 1 >= max_retries THEN 'dead_letter' ELSE 'failed' END,
            completed_at = CASE WHEN retry_count + 1 >= max_retries THEN NOW() ELSE completed_at END,
            retry_count = retry_count + 1,
            error = $2
      WHERE task_id = $1
      RETURNING *`,
    [taskId, error],
  );
  if (!rows[0]) return null;
  const task = parseTask(rows[0]);
  await appendTaskEvent(taskId, task.status === 'dead_letter' ? 'task_dead_lettered' : 'task_failed', { error });
  return task;
}
