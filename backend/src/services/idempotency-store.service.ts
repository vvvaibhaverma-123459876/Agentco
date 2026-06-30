import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';
import { eventLog } from './event-log.service';

export type IdempotencyStatus = 'in_progress' | 'completed' | 'failed';

export interface IdempotencyRecord {
  id: string;
  scope: string;
  idempotency_key: string;
  request_hash: string;
  actor_id: string;
  status: IdempotencyStatus;
  response_json: Record<string, unknown> | null;
  error_message: string | null;
  started_event_log_id: string | null;
  completed_event_log_id: string | null;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BeginIdempotencyInput {
  scope: string;
  idempotencyKey: string;
  actorId: string;
  payload: Record<string, unknown>;
  ttlSeconds?: number;
}

function stable(value: unknown): unknown {
  if (value instanceof Date) return value.toISOString();
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, stable(nested)])
    );
  }
  return value;
}

function requestHash(payload: Record<string, unknown>): string {
  return crypto.createHash('sha256').update(JSON.stringify(stable(payload))).digest('hex');
}

function validateScope(scope: string): void {
  if (!/^[a-z0-9_.:-]{3,120}$/i.test(scope)) {
    throw new Error('idempotency scope must be 3-120 safe characters');
  }
}

function validateKey(key: string): void {
  if (!/^[a-z0-9_.:-]{3,200}$/i.test(key)) {
    throw new Error('idempotency key must be 3-200 safe characters');
  }
}

export class IdempotencyStoreService {
  async begin(input: BeginIdempotencyInput): Promise<{ record: IdempotencyRecord; replay: boolean }> {
    validateScope(input.scope);
    validateKey(input.idempotencyKey);
    const hash = requestHash(input.payload);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const inserted = await client.query<IdempotencyRecord>(
        `INSERT INTO idempotency_records
           (scope, idempotency_key, request_hash, actor_id, status, expires_at)
         VALUES ($1, $2, $3, $4, 'in_progress', CASE WHEN $5::int IS NULL THEN NULL ELSE now() + ($5::int * interval '1 second') END)
         ON CONFLICT (scope, idempotency_key) DO NOTHING
         RETURNING id, scope, idempotency_key, request_hash, actor_id, status, response_json,
                   error_message, started_event_log_id, completed_event_log_id, expires_at, created_at, updated_at`,
        [input.scope, input.idempotencyKey, hash, input.actorId, input.ttlSeconds ?? null]
      );

      if (inserted.rowCount === 1) {
        const started = await eventLog.appendWithClient(client, {
          event_type: 'idempotency.started',
          actor_id: input.actorId,
          object_type: 'idempotency_record',
          payload: {
            scope: input.scope,
            idempotency_key: input.idempotencyKey,
            request_hash: hash,
          },
        });
        const updated = await client.query<IdempotencyRecord>(
          `UPDATE idempotency_records
              SET started_event_log_id = $1, updated_at = now()
            WHERE id = $2
            RETURNING id, scope, idempotency_key, request_hash, actor_id, status, response_json,
                      error_message, started_event_log_id, completed_event_log_id, expires_at, created_at, updated_at`,
          [started.id, inserted.rows[0].id]
        );
        await client.query('COMMIT');
        return { record: updated.rows[0], replay: false };
      }

      const existing = await this.getWithClient(client, input.scope, input.idempotencyKey);
      if (!existing) throw new Error('idempotency record disappeared during begin');
      if (existing.request_hash !== hash) {
        throw new Error('idempotency key reused with different request payload');
      }
      await client.query('COMMIT');
      return { record: existing, replay: existing.status === 'completed' };
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async complete(
    scope: string,
    idempotencyKey: string,
    actorId: string,
    payload: Record<string, unknown>,
    response: Record<string, unknown>
  ): Promise<IdempotencyRecord> {
    validateScope(scope);
    validateKey(idempotencyKey);
    const hash = requestHash(payload);
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const existing = await this.getWithClient(client, scope, idempotencyKey);
      if (!existing) throw new Error('idempotency record does not exist');
      if (existing.request_hash !== hash) {
        throw new Error('idempotency key reused with different request payload');
      }
      if (existing.status === 'completed') {
        await client.query('COMMIT');
        return existing;
      }

      const completed = await eventLog.appendWithClient(client, {
        event_type: 'idempotency.completed',
        actor_id: actorId,
        object_type: 'idempotency_record',
        payload: {
          scope,
          idempotency_key: idempotencyKey,
          request_hash: hash,
        },
      });
      const updated = await client.query<IdempotencyRecord>(
        `UPDATE idempotency_records
            SET status = 'completed',
                response_json = $1::jsonb,
                error_message = NULL,
                completed_event_log_id = $2,
                updated_at = now()
          WHERE scope = $3 AND idempotency_key = $4
          RETURNING id, scope, idempotency_key, request_hash, actor_id, status, response_json,
                    error_message, started_event_log_id, completed_event_log_id, expires_at, created_at, updated_at`,
        [JSON.stringify(response), completed.id, scope, idempotencyKey]
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

  async get(scope: string, idempotencyKey: string): Promise<IdempotencyRecord | null> {
    validateScope(scope);
    validateKey(idempotencyKey);
    const result = await db.query<IdempotencyRecord>(
      `SELECT id, scope, idempotency_key, request_hash, actor_id, status, response_json,
              error_message, started_event_log_id, completed_event_log_id, expires_at, created_at, updated_at
         FROM idempotency_records
        WHERE scope = $1 AND idempotency_key = $2`,
      [scope, idempotencyKey]
    );
    return result.rows[0] ?? null;
  }

  private async getWithClient(client: PoolClient, scope: string, idempotencyKey: string): Promise<IdempotencyRecord | null> {
    const result = await client.query<IdempotencyRecord>(
      `SELECT id, scope, idempotency_key, request_hash, actor_id, status, response_json,
              error_message, started_event_log_id, completed_event_log_id, expires_at, created_at, updated_at
         FROM idempotency_records
        WHERE scope = $1 AND idempotency_key = $2
        FOR UPDATE`,
      [scope, idempotencyKey]
    );
    return result.rows[0] ?? null;
  }
}

export const idempotencyStore = new IdempotencyStoreService();
