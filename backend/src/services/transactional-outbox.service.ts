import { PoolClient } from 'pg';
import { db } from '../db/client';

export interface OutboxEnvelope {
  event_id: string;
  event_type: string;
  actor_id: string;
  occurred_at: string;
  payload: Record<string, unknown>;
  correlation_id: string;
  causation_id: string | null;
  object_type: string | null;
  object_id: string | null;
  event_hash: string;
}

export interface OutboxRecord {
  id: string;
  event_log_id: string;
  topic: string;
  envelope: OutboxEnvelope;
  status: 'pending' | 'publishing' | 'published' | 'failed' | 'dead_lettered';
  attempts: number;
  last_error: string | null;
}

export interface OutboxPublisher {
  publish(topic: string, envelope: OutboxEnvelope): Promise<void>;
}

function topicForEventType(eventType: string): string {
  const domain = eventType.split('.')[0];
  const known: Record<string, string> = {
    actor: 'agentco.identity',
    role: 'agentco.identity',
    permission: 'agentco.identity',
    resource: 'agentco.resources',
    test: 'agentco.test',
  };
  return known[domain] ?? 'agentco.events';
}

function requirePositiveInteger(value: number, field: string): void {
  if (!Number.isInteger(value) || value <= 0) throw new Error(`${field} must be a positive integer`);
}

export class TransactionalOutboxService {
  async enqueueWithClient(
    client: PoolClient,
    input: {
      eventLogId: string;
      eventType: string;
      actorId: string;
      occurredAt: string;
      payload: Record<string, unknown>;
      correlationId: string;
      causationId: string | null;
      objectType: string | null;
      objectId: string | null;
      eventHash: string;
    }
  ): Promise<OutboxRecord> {
    const topic = topicForEventType(input.eventType);
    const envelope: OutboxEnvelope = {
      event_id: input.eventLogId,
      event_type: input.eventType,
      actor_id: input.actorId,
      occurred_at: input.occurredAt,
      payload: input.payload,
      correlation_id: input.correlationId,
      causation_id: input.causationId,
      object_type: input.objectType,
      object_id: input.objectId,
      event_hash: input.eventHash,
    };

    const result = await client.query<OutboxRecord>(
      `INSERT INTO event_outbox (event_log_id, topic, envelope)
       VALUES ($1,$2,$3::jsonb)
       ON CONFLICT (event_log_id)
       DO UPDATE SET updated_at = event_outbox.updated_at
       RETURNING id, event_log_id, topic, envelope, status, attempts, last_error`,
      [input.eventLogId, topic, JSON.stringify(envelope)]
    );
    return result.rows[0];
  }

  async relayBatch(
    publisher: OutboxPublisher,
    options: { limit?: number; workerId?: string; maxAttempts?: number } = {}
  ): Promise<{ published: number; failed: number; dead_lettered: number }> {
    const limit = options.limit ?? 50;
    const maxAttempts = options.maxAttempts ?? 5;
    requirePositiveInteger(limit, 'limit');
    requirePositiveInteger(maxAttempts, 'maxAttempts');
    const workerId = options.workerId ?? `outbox-relay-${process.pid}`;

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const claimed = await client.query<OutboxRecord>(
        `UPDATE event_outbox
            SET status = 'publishing',
                locked_by = $1,
                locked_at = now(),
                updated_at = now()
          WHERE id IN (
            SELECT id
              FROM event_outbox
             WHERE status IN ('pending', 'failed')
               AND next_attempt_at <= now()
             ORDER BY created_at ASC
             LIMIT $2
             FOR UPDATE SKIP LOCKED
          )
          RETURNING id, event_log_id, topic, envelope, status, attempts, last_error`,
        [workerId, limit]
      );
      await client.query('COMMIT');

      let published = 0;
      let failed = 0;
      let deadLettered = 0;
      for (const record of claimed.rows) {
        try {
          await publisher.publish(record.topic, record.envelope);
          await db.query(
            `UPDATE event_outbox
                SET status = 'published',
                    published_at = now(),
                    locked_by = NULL,
                    locked_at = NULL,
                    last_error = NULL,
                    updated_at = now()
              WHERE id = $1`,
            [record.id]
          );
          published += 1;
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          const attempts = record.attempts + 1;
          if (attempts >= maxAttempts) {
            await this.deadLetter(record, attempts, message);
            deadLettered += 1;
          } else {
            await db.query(
              `UPDATE event_outbox
                  SET status = 'failed',
                      attempts = $2,
                      next_attempt_at = now() + ($3::text || ' seconds')::interval,
                      locked_by = NULL,
                      locked_at = NULL,
                      last_error = $4,
                      updated_at = now()
                WHERE id = $1`,
              [record.id, attempts, Math.min(300, Math.pow(2, attempts)), message]
            );
            failed += 1;
          }
        }
      }

      return { published, failed, dead_lettered: deadLettered };
    } catch (error) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  }

  async pendingCount(): Promise<number> {
    const result = await db.query<{ count: string }>(
      `SELECT COUNT(*)::text AS count
         FROM event_outbox
        WHERE status IN ('pending', 'failed', 'publishing')`
    );
    return Number(result.rows[0]?.count ?? 0);
  }

  private async deadLetter(record: OutboxRecord, attempts: number, error: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await client.query(
        `UPDATE event_outbox
            SET status = 'dead_lettered',
                attempts = $2,
                locked_by = NULL,
                locked_at = NULL,
                last_error = $3,
                updated_at = now()
          WHERE id = $1`,
        [record.id, attempts, error]
      );
      await client.query(
        `INSERT INTO event_dead_letters (outbox_id, event_log_id, topic, envelope, attempts, error)
         VALUES ($1,$2,$3,$4::jsonb,$5,$6)
         ON CONFLICT (outbox_id) DO NOTHING`,
        [record.id, record.event_log_id, record.topic, JSON.stringify(record.envelope), attempts, error]
      );
      await client.query('COMMIT');
    } catch (deadLetterError) {
      await client.query('ROLLBACK');
      throw deadLetterError;
    } finally {
      client.release();
    }
  }
}

export const transactionalOutbox = new TransactionalOutboxService();
