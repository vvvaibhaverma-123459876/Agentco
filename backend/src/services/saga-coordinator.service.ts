import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export interface SagaExecution {
  id: string;
  saga_type: string;
  status: 'running' | 'completed' | 'failed' | 'compensating' | 'compensated';
  actor_id: string;
  correlation_id: string;
  payload: Record<string, unknown>;
  failure_reason: string | null;
  event_log_id: string | null;
}

export interface SagaStep {
  id: string;
  saga_id: string;
  step_name: string;
  step_order: number;
  status:
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'compensation_pending'
    | 'compensated'
    | 'compensation_failed';
  task_id: string | null;
  payload: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  event_log_id: string | null;
}

function assertUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

async function requireActiveActor(client: PoolClient, actorId: string): Promise<void> {
  const actor = await client.query('SELECT 1 FROM actors WHERE id = $1 AND status = $2', [actorId, 'active']);
  if (actor.rowCount !== 1) throw new Error(`saga actor is not active: ${actorId}`);
}

export class SagaCoordinatorService {
  async startSaga(input: {
    saga_type: string;
    actor_id: string;
    payload?: Record<string, unknown>;
    correlation_id?: string;
  }): Promise<SagaExecution> {
    if (!input.saga_type?.trim()) throw new Error('saga_type is required');
    assertUuid(input.actor_id, 'actor_id');
    if (input.correlation_id) assertUuid(input.correlation_id, 'correlation_id');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await requireActiveActor(client, input.actor_id);
      const inserted = await client.query<SagaExecution>(
        `INSERT INTO saga_executions (saga_type, actor_id, correlation_id, payload)
         VALUES ($1, $2, COALESCE($3::uuid, gen_random_uuid()), $4::jsonb)
         RETURNING id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id`,
        [input.saga_type, input.actor_id, input.correlation_id ?? null, JSON.stringify(input.payload ?? {})]
      );
      const saga = inserted.rows[0];
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.started',
        actor_id: input.actor_id,
        object_type: 'saga_execution',
        object_id: saga.id,
        correlation_id: saga.correlation_id,
        payload: { saga_id: saga.id, saga_type: saga.saga_type, payload: saga.payload },
      });
      const updated = await client.query<SagaExecution>(
        `UPDATE saga_executions SET event_log_id = $2, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id`,
        [saga.id, event.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async addStep(input: {
    saga_id: string;
    step_name: string;
    step_order: number;
    payload?: Record<string, unknown>;
    task_id?: string | null;
    compensation_payload?: Record<string, unknown>;
  }): Promise<SagaStep> {
    assertUuid(input.saga_id, 'saga_id');
    if (!input.step_name?.trim()) throw new Error('step_name is required');
    if (!Number.isInteger(input.step_order) || input.step_order < 0) throw new Error('step_order must be a non-negative integer');
    if (input.task_id) assertUuid(input.task_id, 'task_id');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const saga = await this.getRunningSagaForUpdate(client, input.saga_id);
      const result = await client.query<SagaStep>(
        `INSERT INTO saga_steps (saga_id, step_name, step_order, task_id, payload, compensation_payload)
         VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb)
         RETURNING id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id`,
        [
          input.saga_id,
          input.step_name,
          input.step_order,
          input.task_id ?? null,
          JSON.stringify(input.payload ?? {}),
          input.compensation_payload ? JSON.stringify(input.compensation_payload) : null,
        ]
      );
      const step = result.rows[0];
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.step_added',
        actor_id: saga.actor_id,
        object_type: 'saga_step',
        object_id: step.id,
        correlation_id: saga.correlation_id,
        causation_id: saga.event_log_id,
        payload: { saga_id: saga.id, step_id: step.id, step_name: step.step_name, step_order: step.step_order },
      });
      const updated = await client.query<SagaStep>(
        `UPDATE saga_steps SET event_log_id = $2, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id`,
        [step.id, event.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async startStep(stepId: string): Promise<SagaStep> {
    assertUuid(stepId, 'step_id');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await this.getStepAndSagaForUpdate(client, stepId);
      if (current.step.status !== 'pending') throw new Error(`step is not pending: ${current.step.status}`);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.step_started',
        actor_id: current.saga.actor_id,
        object_type: 'saga_step',
        object_id: stepId,
        correlation_id: current.saga.correlation_id,
        causation_id: current.step.event_log_id ?? current.saga.event_log_id,
        payload: { saga_id: current.saga.id, step_id: stepId, step_name: current.step.step_name },
      });
      const updated = await client.query<SagaStep>(
        `UPDATE saga_steps
            SET status = 'running', started_at = now(), event_log_id = $2, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id`,
        [stepId, event.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async completeStep(stepId: string, result: Record<string, unknown> = {}): Promise<SagaStep> {
    assertUuid(stepId, 'step_id');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await this.getStepAndSagaForUpdate(client, stepId);
      if (current.step.status !== 'running') throw new Error(`step is not running: ${current.step.status}`);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.step_completed',
        actor_id: current.saga.actor_id,
        object_type: 'saga_step',
        object_id: stepId,
        correlation_id: current.saga.correlation_id,
        causation_id: current.step.event_log_id ?? current.saga.event_log_id,
        payload: { saga_id: current.saga.id, step_id: stepId, step_name: current.step.step_name, result },
      });
      const updated = await client.query<SagaStep>(
        `UPDATE saga_steps
            SET status = 'completed', completed_at = now(), result = $2::jsonb, event_log_id = $3, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id`,
        [stepId, JSON.stringify(result), event.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async completeSaga(sagaId: string): Promise<SagaExecution> {
    assertUuid(sagaId, 'saga_id');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const saga = await this.getRunningSagaForUpdate(client, sagaId);
      const open = await client.query<{ count: string }>(
        `SELECT COUNT(*)::text AS count FROM saga_steps
          WHERE saga_id = $1 AND status NOT IN ('completed', 'compensated')`,
        [sagaId]
      );
      if (Number(open.rows[0].count) > 0) throw new Error('cannot complete saga with incomplete steps');
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.completed',
        actor_id: saga.actor_id,
        object_type: 'saga_execution',
        object_id: sagaId,
        correlation_id: saga.correlation_id,
        causation_id: saga.event_log_id,
        payload: { saga_id: saga.id, saga_type: saga.saga_type },
      });
      const updated = await client.query<SagaExecution>(
        `UPDATE saga_executions
            SET status = 'completed', completed_at = now(), event_log_id = $2, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id`,
        [sagaId, event.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async failStepAndCompensate(stepId: string, errorMessage: string): Promise<SagaExecution> {
    assertUuid(stepId, 'step_id');
    if (!errorMessage.trim()) throw new Error('errorMessage is required');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await this.getStepAndSagaForUpdate(client, stepId);
      if (!['pending', 'running'].includes(current.step.status)) throw new Error(`step cannot fail from status: ${current.step.status}`);
      const failureEvent = await eventLog.appendWithClient(client, {
        event_type: 'saga.step_failed',
        actor_id: current.saga.actor_id,
        object_type: 'saga_step',
        object_id: stepId,
        correlation_id: current.saga.correlation_id,
        causation_id: current.step.event_log_id ?? current.saga.event_log_id,
        payload: { saga_id: current.saga.id, step_id: stepId, step_name: current.step.step_name, error: errorMessage },
      });
      await client.query(
        `UPDATE saga_steps
            SET status = 'failed', error = $2, event_log_id = $3, updated_at = now()
          WHERE id = $1`,
        [stepId, errorMessage, failureEvent.id]
      );
      await client.query(
        `UPDATE saga_steps
            SET status = 'compensation_pending', updated_at = now()
          WHERE saga_id = $1 AND status = 'completed'`,
        [current.saga.id]
      );
      const sagaEvent = await eventLog.appendWithClient(client, {
        event_type: 'saga.compensation_required',
        actor_id: current.saga.actor_id,
        object_type: 'saga_execution',
        object_id: current.saga.id,
        correlation_id: current.saga.correlation_id,
        causation_id: failureEvent.id,
        payload: { saga_id: current.saga.id, failed_step_id: stepId, error: errorMessage },
      });
      const updated = await client.query<SagaExecution>(
        `UPDATE saga_executions
            SET status = 'compensating', failure_reason = $2, event_log_id = $3, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id`,
        [current.saga.id, errorMessage, sagaEvent.id]
      );
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async markStepCompensated(stepId: string, result: Record<string, unknown> = {}): Promise<SagaStep> {
    assertUuid(stepId, 'step_id');
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const current = await this.getStepAndSagaForUpdate(client, stepId);
      if (current.step.status !== 'compensation_pending') throw new Error(`step is not compensation_pending: ${current.step.status}`);
      const event = await eventLog.appendWithClient(client, {
        event_type: 'saga.step_compensated',
        actor_id: current.saga.actor_id,
        object_type: 'saga_step',
        object_id: stepId,
        correlation_id: current.saga.correlation_id,
        causation_id: current.step.event_log_id ?? current.saga.event_log_id,
        payload: { saga_id: current.saga.id, step_id: stepId, result },
      });
      const updated = await client.query<SagaStep>(
        `UPDATE saga_steps
            SET status = 'compensated', result = $2::jsonb, event_log_id = $3, updated_at = now()
          WHERE id = $1
          RETURNING id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id`,
        [stepId, JSON.stringify(result), event.id]
      );
      const open = await client.query<{ count: string }>(
        `SELECT COUNT(*)::text AS count
           FROM saga_steps
          WHERE saga_id = $1 AND status = 'compensation_pending'`,
        [current.saga.id]
      );
      if (Number(open.rows[0].count) === 0) {
        await client.query(
          `UPDATE saga_executions SET status = 'compensated', completed_at = now(), updated_at = now()
            WHERE id = $1 AND status = 'compensating'`,
          [current.saga.id]
        );
      }
      await client.query('COMMIT');
      return updated.rows[0];
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async getSaga(sagaId: string): Promise<(SagaExecution & { steps: SagaStep[] }) | null> {
    assertUuid(sagaId, 'saga_id');
    const saga = await db.query<SagaExecution>(
      `SELECT id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id
         FROM saga_executions WHERE id = $1`,
      [sagaId]
    );
    if (saga.rowCount !== 1) return null;
    const steps = await db.query<SagaStep>(
      `SELECT id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id
         FROM saga_steps WHERE saga_id = $1 ORDER BY step_order ASC`,
      [sagaId]
    );
    return { ...saga.rows[0], steps: steps.rows };
  }

  private async getRunningSagaForUpdate(client: PoolClient, sagaId: string): Promise<SagaExecution> {
    const saga = await client.query<SagaExecution>(
      `SELECT id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id
         FROM saga_executions WHERE id = $1 FOR UPDATE`,
      [sagaId]
    );
    if (saga.rowCount !== 1) throw new Error(`saga not found: ${sagaId}`);
    if (saga.rows[0].status !== 'running') throw new Error(`saga is not running: ${saga.rows[0].status}`);
    return saga.rows[0];
  }

  private async getStepAndSagaForUpdate(client: PoolClient, stepId: string): Promise<{ step: SagaStep; saga: SagaExecution }> {
    const step = await client.query<SagaStep>(
      `SELECT id, saga_id, step_name, step_order, status, task_id, payload, result, error, event_log_id
         FROM saga_steps WHERE id = $1 FOR UPDATE`,
      [stepId]
    );
    if (step.rowCount !== 1) throw new Error(`saga step not found: ${stepId}`);
    const saga = await client.query<SagaExecution>(
      `SELECT id, saga_type, status, actor_id, correlation_id, payload, failure_reason, event_log_id
         FROM saga_executions WHERE id = $1 FOR UPDATE`,
      [step.rows[0].saga_id]
    );
    if (saga.rowCount !== 1) throw new Error(`saga not found: ${step.rows[0].saga_id}`);
    if (!['running', 'compensating'].includes(saga.rows[0].status)) throw new Error(`saga is not active: ${saga.rows[0].status}`);
    return { step: step.rows[0], saga: saga.rows[0] };
  }
}

export const sagaCoordinator = new SagaCoordinatorService();
