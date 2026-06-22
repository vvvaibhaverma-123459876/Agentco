import crypto from 'crypto';
import { query, withClient } from '../db/client';
import { auditLog } from './audit-log.service';
import { eventBus } from './event-bus.service';
import { provenance } from './provenance.service';

export type TaskStatus = 'queued' | 'running' | 'done' | 'failed' | 'blocked';

export interface WorkflowTask {
  task_id: string;
  agent_id: string;
  task_type: string;
  payload: Record<string, unknown>;
  queued_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  status: TaskStatus;
  result?: unknown;
  error?: string | null;
  audit_log_id?: string | null;
  event_id?: string | null;
  action_attestation_id?: string | null;
}

export class DurableExecutionService {
  async enqueue(agent_id: string, task_type: string, payload: Record<string, unknown>): Promise<WorkflowTask> {
    const rows = await query<WorkflowTask>(
      `INSERT INTO workflow_tasks (agent_id, task_type, payload, status)
       VALUES ($1,$2,$3,'queued') RETURNING *`,
      [agent_id, task_type, JSON.stringify(payload)],
    );
    return rows[0];
  }

  async get(task_id: string): Promise<WorkflowTask | null> {
    const rows = await query<WorkflowTask>('SELECT * FROM workflow_tasks WHERE task_id=$1', [task_id]);
    return rows[0] ?? null;
  }

  async list(): Promise<WorkflowTask[]> {
    return query<WorkflowTask>('SELECT * FROM workflow_tasks ORDER BY queued_at DESC LIMIT 200');
  }

  async run(task_id: string): Promise<WorkflowTask> {
    const task = await this.claim(task_id);
    if (!task) throw new Error(`task not found or not runnable: ${task_id}`);
    try {
      const result = await this.dispatch(task);
      const confidence_score = 0.8;
      const risk_level = 'low' as const;
      const attestation = await provenance.attestAction({
        principal_id: task.agent_id,
        tool_id: task.task_type,
        input: task.payload,
        output: result,
        trusted_confidence: confidence_score,
        risk_level,
        tee_quote: 'local-measured-backend-dispatch-v1',
      });
      const log_id = await auditLog.append({
        agent_id: task.agent_id,
        action_type: 'decision',
        input_summary: JSON.stringify({ task_type: task.task_type, payload: task.payload }).slice(0, 500),
        output_summary: JSON.stringify(result).slice(0, 500),
        confidence_score,
        risk_level,
        session_id: task.task_id,
      });
      const event_id = crypto.randomUUID();
      await eventBus.publish({
        event_id,
        event_type: `${task.agent_id}.task_completed`,
        producer_agent_id: task.agent_id,
        timestamp: new Date().toISOString(),
        confidence_score,
        payload: { task_id: task.task_id, task_type: task.task_type, log_id, action_id: attestation.action_id },
        correlation_id: task.task_id,
        risk_level,
        requires_ack: false,
      }).catch(() => undefined);
      await query(
        `UPDATE workflow_tasks
         SET status='done', completed_at=now(), result=$2, audit_log_id=$3, event_id=$4, action_attestation_id=$5
         WHERE task_id=$1`,
        [task.task_id, JSON.stringify(result), log_id, event_id, attestation.action_id],
      );
    } catch (err) {
      await query(
        `UPDATE workflow_tasks SET status='failed', completed_at=now(), error=$2 WHERE task_id=$1`,
        [task.task_id, String(err)],
      );
    }
    return (await this.get(task.task_id)) as WorkflowTask;
  }

  private async claim(task_id: string): Promise<WorkflowTask | null> {
    return withClient(async client => {
      await client.query('BEGIN');
      const { rows } = await client.query<WorkflowTask>(
        `UPDATE workflow_tasks
         SET status='running', started_at=now(), claimed_by='backend-dispatcher'
         WHERE task_id=$1 AND status IN ('queued','failed')
         RETURNING *`,
        [task_id],
      );
      await client.query('COMMIT');
      return rows[0] ?? null;
    });
  }

  private async dispatch(task: WorkflowTask): Promise<Record<string, unknown>> {
    if (task.task_type === 'health_check') {
      return {
        kind: 'health_check_result',
        agent_id: task.agent_id,
        received_payload_hash: crypto.createHash('sha256').update(JSON.stringify(task.payload)).digest('hex'),
        executed_by: 'durable-execution-service',
      };
    }
    if (task.task_type === 'record_observation') {
      return {
        kind: 'observation_recorded',
        agent_id: task.agent_id,
        observation: task.payload,
        executed_by: 'durable-execution-service',
      };
    }
    throw new Error(`unsupported durable task_type: ${task.task_type}`);
  }
}

export const durableExecution = new DurableExecutionService();
