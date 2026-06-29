import crypto from 'crypto';
import { PoolClient } from 'pg';
import { db } from '../db/client';

export interface EventLogAppendInput {
  id?: string;
  event_type: string;
  actor_id: string;
  institution_id?: string | null;
  object_type?: string | null;
  object_id?: string | null;
  payload: Record<string, unknown>;
  correlation_id?: string;
  causation_id?: string | null;
  occurred_at?: string;
  signature?: string | null;
}

export interface EventLogRecord {
  id: string;
  event_type: string;
  actor_id: string;
  institution_id: string | null;
  object_type: string | null;
  object_id: string | null;
  occurred_at: string;
  payload: Record<string, unknown>;
  correlation_id: string;
  causation_id: string | null;
  signature: string | null;
  prev_hash: string;
  event_hash: string;
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

function normalizeTimestamp(value: string | Date): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function canonicalEvent(fields: {
  id: string;
  event_type: string;
  actor_id: string;
  institution_id: string | null;
  object_type: string | null;
  object_id: string | null;
  occurred_at: string;
  payload: Record<string, unknown>;
  correlation_id: string;
  causation_id: string | null;
  signature: string | null;
  prev_hash: string;
}): string {
  return JSON.stringify(stable(fields));
}

function requireUuid(value: string, field: string): void {
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value)) {
    throw new Error(`${field} must be a UUID`);
  }
}

export class EventLogService {
  async append(input: EventLogAppendInput): Promise<EventLogRecord> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const record = await this.appendWithClient(client, input);
      await client.query('COMMIT');
      return record;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async appendWithClient(client: PoolClient, input: EventLogAppendInput): Promise<EventLogRecord> {
    this.validate(input);
    const id = input.id ?? crypto.randomUUID();
    const occurredAt = normalizeTimestamp(input.occurred_at ?? new Date());
    const correlationId = input.correlation_id ?? crypto.randomUUID();

    const actor = await client.query('SELECT 1 FROM actors WHERE id = $1 AND status = $2', [input.actor_id, 'active']);
    if (actor.rowCount !== 1) {
      throw new Error(`event actor is not active: ${input.actor_id}`);
    }

    const previous = await client.query<{ event_hash: string }>(
      `SELECT event_hash
         FROM event_log
        ORDER BY occurred_at DESC, id DESC
        LIMIT 1`
    );
    const prevHash = previous.rows[0]?.event_hash ?? '0'.repeat(64);
    const fields = {
      id,
      event_type: input.event_type,
      actor_id: input.actor_id,
      institution_id: input.institution_id ?? null,
      object_type: input.object_type ?? null,
      object_id: input.object_id ?? null,
      occurred_at: occurredAt,
      payload: input.payload,
      correlation_id: correlationId,
      causation_id: input.causation_id ?? null,
      signature: input.signature ?? null,
      prev_hash: prevHash,
    };
    const eventHash = crypto.createHash('sha256').update(prevHash + canonicalEvent(fields)).digest('hex');

    const result = await client.query<EventLogRecord>(
      `INSERT INTO event_log
         (id, event_type, actor_id, institution_id, object_type, object_id,
          occurred_at, payload, correlation_id, causation_id, signature, prev_hash, event_hash)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10,$11,$12,$13)
       RETURNING id, event_type, actor_id, institution_id, object_type, object_id,
                 occurred_at, payload, correlation_id, causation_id, signature, prev_hash, event_hash`,
      [
        id,
        input.event_type,
        input.actor_id,
        input.institution_id ?? null,
        input.object_type ?? null,
        input.object_id ?? null,
        occurredAt,
        JSON.stringify(input.payload),
        correlationId,
        input.causation_id ?? null,
        input.signature ?? null,
        prevHash,
        eventHash,
      ]
    );

    return result.rows[0];
  }

  async verifyChainIntegrity(): Promise<{ valid: boolean; broken_at?: string }> {
    const result = await db.query<{
      id: string;
      event_type: string;
      actor_id: string;
      institution_id: string | null;
      object_type: string | null;
      object_id: string | null;
      occurred_at: string | Date;
      payload: Record<string, unknown>;
      correlation_id: string;
      causation_id: string | null;
      signature: string | null;
      prev_hash: string;
      event_hash: string;
    }>(
      `SELECT id, event_type, actor_id, institution_id, object_type, object_id,
              occurred_at, payload, correlation_id, causation_id, signature, prev_hash, event_hash
         FROM event_log
        ORDER BY occurred_at ASC, id ASC`
    );

    let expectedPrev = result.rows[0]?.prev_hash ?? '';
    for (const row of result.rows) {
      if (row.prev_hash !== expectedPrev) {
        return { valid: false, broken_at: row.id };
      }
      const computed = crypto
        .createHash('sha256')
        .update(
          row.prev_hash +
            canonicalEvent({
              id: row.id,
              event_type: row.event_type,
              actor_id: row.actor_id,
              institution_id: row.institution_id,
              object_type: row.object_type,
              object_id: row.object_id,
              occurred_at: normalizeTimestamp(row.occurred_at),
              payload: row.payload,
              correlation_id: row.correlation_id,
              causation_id: row.causation_id,
              signature: row.signature,
              prev_hash: row.prev_hash,
            })
        )
        .digest('hex');
      if (computed !== row.event_hash) {
        return { valid: false, broken_at: row.id };
      }
      expectedPrev = row.event_hash;
    }
    return { valid: true };
  }

  private validate(input: EventLogAppendInput): void {
    if (input.id) requireUuid(input.id, 'id');
    requireUuid(input.actor_id, 'actor_id');
    if (input.institution_id) requireUuid(input.institution_id, 'institution_id');
    if (input.object_id) requireUuid(input.object_id, 'object_id');
    if (input.correlation_id) requireUuid(input.correlation_id, 'correlation_id');
    if (input.causation_id) requireUuid(input.causation_id, 'causation_id');
    if (!input.event_type?.trim()) throw new Error('event_type is required');
    if (!input.payload || typeof input.payload !== 'object' || Array.isArray(input.payload)) {
      throw new Error('payload must be an object');
    }
  }
}

export const eventLog = new EventLogService();
