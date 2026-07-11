/**
 * Event Bus Service — real Kafka produce/consume.
 *
 * Real implementation:
 *   publish()  → KafkaJS producer.send(); also INSERTs into event_history (Postgres).
 *   consume()  → KafkaJS consumer.run(); verifies HMAC before calling handler.
 * HMAC-SHA256 signing on all events; malformed or unsigned envelopes are rejected
 * before the handler is called. Duplicate events (same event_id) are idempotent
 * thanks to the UUID primary key on event_history.
 */
import crypto from 'crypto';
import { db, query } from '../db/client';
import { getProducer, createConsumer } from '../db/kafka';
import { auditLog } from './audit-log.service';

const SIGNING_KEY = process.env.EVENT_BUS_SIGNING_KEY ?? 'dev-key-replace-in-production';

export interface AgentEvent {
  event_id: string;
  event_type: string;
  producer_agent_id: string;
  timestamp: string;
  confidence_score: number;
  payload: Record<string, unknown>;
  correlation_id?: string;
  risk_level: 'low' | 'medium' | 'high' | 'critical';
  requires_ack: boolean;
  ttl_seconds?: number;
}

export interface SignedEvent extends AgentEvent {
  signature: string;
}

type EventBusOutboxRow = {
  event_id: string;
  topic: string;
  signed_envelope: SignedEvent;
  attempts: number;
};

export const KAFKA_TOPICS: Record<string, string> = {
  research:    'agentco.research',
  product:     'agentco.product',
  engineering: 'agentco.engineering',
  sales:       'agentco.sales',
  cx:          'agentco.cx',
  finance:     'agentco.finance',
  people:      'agentco.people',
  legal:       'agentco.legal',
  override:    'agentco.override',
  audit:       'agentco.audit',
  events:      'agentco.events',
  decisions:   'agentco.decisions',
};

function topicForEventType(eventType: string): string {
  const domain = eventType.split('.')[0];
  return KAFKA_TOPICS[domain] ?? 'agentco.events';
}

function isProductionLike(): boolean {
  return process.env.AGENTCO_ENV === 'production' || process.env.AGENTCO_ENV === 'staging' || process.env.NODE_ENV === 'production';
}

function deliveryMode(): 'sync' | 'outbox' {
  const configured = process.env.EVENT_BUS_DELIVERY_MODE;
  if (configured === 'sync' || configured === 'outbox') return configured;
  return isProductionLike() ? 'outbox' : 'sync';
}

function sign(event: AgentEvent): string {
  const payload = JSON.stringify(event);
  return crypto.createHmac('sha256', SIGNING_KEY).update(payload).digest('hex');
}

function verify(signed: SignedEvent): boolean {
  const { signature, ...event } = signed;
  const expected = sign(event as AgentEvent);
  try {
    return crypto.timingSafeEqual(
      Buffer.from(signature, 'hex'),
      Buffer.from(expected, 'hex')
    );
  } catch {
    return false;  // mismatched lengths → bad signature
  }
}

export class EventBusService {
  /**
   * Publish a signed event to Kafka and persist it to event_history.
   * ON CONFLICT DO NOTHING on event_id makes repeated publishes idempotent.
   */
  async publish(event: AgentEvent): Promise<void> {
    this.validateEnvelope(event);
    const signed: SignedEvent = { ...event, signature: sign(event) };
    const topic = topicForEventType(event.event_type);

    if (deliveryMode() === 'outbox') {
      await this.persistHistoryAndOutbox(event, signed, topic);
      await this.auditPublish(event, topic, 'scheduled');
      return;
    }

    // 1. Produce to Kafka
    const producer = await getProducer();
    await producer.send({
      topic,
      messages: [{ key: event.event_id, value: JSON.stringify(signed) }],
    });

    // 2. Persist to event_history (append-only, idempotent)
    await this.persistHistory(event);

    // 3. Audit the publish
    await this.auditPublish(event, topic, 'published');
  }

  private async persistHistory(event: AgentEvent): Promise<void> {
    await query(
      `INSERT INTO event_history
         (event_id, event_type, producer_agent_id, timestamp, confidence_score,
          payload, correlation_id, risk_level, requires_ack, ttl_seconds)
       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
       ON CONFLICT (event_id) DO NOTHING`,
      [
        event.event_id,
        event.event_type,
        event.producer_agent_id,
        event.timestamp,
        event.confidence_score,
        JSON.stringify(event.payload),
        event.correlation_id ?? null,
        event.risk_level,
        event.requires_ack,
        event.ttl_seconds ?? 86400,
      ]
    );
  }

  private async persistHistoryAndOutbox(event: AgentEvent, signed: SignedEvent, topic: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await client.query(
        `INSERT INTO event_history
           (event_id, event_type, producer_agent_id, timestamp, confidence_score,
            payload, correlation_id, risk_level, requires_ack, ttl_seconds)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
         ON CONFLICT (event_id) DO NOTHING`,
        [
          event.event_id,
          event.event_type,
          event.producer_agent_id,
          event.timestamp,
          event.confidence_score,
          JSON.stringify(event.payload),
          event.correlation_id ?? null,
          event.risk_level,
          event.requires_ack,
          event.ttl_seconds ?? 86400,
        ]
      );
      await client.query(
        `INSERT INTO event_bus_outbox (event_id, topic, signed_envelope)
         VALUES ($1,$2,$3::jsonb)
         ON CONFLICT (event_id)
         DO UPDATE SET updated_at = event_bus_outbox.updated_at`,
        [event.event_id, topic, JSON.stringify(signed)]
      );
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw error;
    } finally {
      client.release();
    }
  }

  private async auditPublish(event: AgentEvent, topic: string, deliveryState: 'published' | 'scheduled'): Promise<void> {
    await auditLog.append({
      agent_id: event.producer_agent_id,
      action_type: 'event_published',
      input_summary: `event_type=${event.event_type} topic=${topic} delivery=${deliveryState}`,
      output_summary: `event_id=${event.event_id}`,
      confidence_score: event.confidence_score,
      risk_level: event.risk_level,
    }).catch(err => console.error('[AUDIT_FAILURE_ON_PUBLISH]', err));
  }

  /**
   * Subscribe to a Kafka topic. Verifies HMAC before calling handler.
   * Malformed or unsigned envelopes are logged and skipped — never forwarded.
   */
  async consume(
    topic: string,
    groupId: string,
    handler: (event: AgentEvent) => Promise<void>
  ): Promise<void> {
    const consumer = createConsumer(groupId);
    await consumer.connect();
    await consumer.subscribe({ topic, fromBeginning: false });

    await consumer.run({
      eachMessage: async ({ message }) => {
        if (!message.value) return;

        let signed: SignedEvent;
        try {
          signed = JSON.parse(message.value.toString());
        } catch {
          console.error('[EVENT_BUS] Malformed envelope — not valid JSON');
          return;
        }

        if (!this.verifySignature(signed)) {
          console.error(
            '[EVENT_BUS] HMAC verification failed for event_id=%s — discarding',
            signed.event_id
          );
          return;
        }

        const { signature: _sig, ...event } = signed;
        await handler(event as AgentEvent);
      },
    });
  }

  validateEnvelope(event: AgentEvent): void {
    const required: (keyof AgentEvent)[] = [
      'event_id', 'event_type', 'producer_agent_id', 'timestamp',
      'confidence_score', 'payload', 'risk_level', 'requires_ack',
    ];
    for (const field of required) {
      if (event[field] === undefined || event[field] === null) {
        throw new Error(`Event envelope missing required field: ${field}`);
      }
    }
    if (event.confidence_score < 0 || event.confidence_score > 1) {
      throw new Error(`Event confidence_score out of range: ${event.confidence_score}`);
    }
  }

  verifySignature(signed: SignedEvent): boolean {
    return verify(signed);
  }

  async relayOutboxBatch(options: { limit?: number; workerId?: string; maxAttempts?: number } = {}): Promise<{
    published: number;
    failed: number;
    dead_lettered: number;
  }> {
    const limit = options.limit ?? 50;
    const maxAttempts = options.maxAttempts ?? 5;
    const workerId = options.workerId ?? `event-bus-outbox-${process.pid}`;
    if (!Number.isInteger(limit) || limit <= 0) throw new Error('limit must be a positive integer');
    if (!Number.isInteger(maxAttempts) || maxAttempts <= 0) throw new Error('maxAttempts must be a positive integer');

    const client = await db.connect();
    try {
      await client.query('BEGIN');
      const claimed = await client.query<EventBusOutboxRow>(
        `UPDATE event_bus_outbox
            SET status = 'publishing',
                locked_by = $1,
                locked_at = now(),
                updated_at = now()
          WHERE event_id IN (
            SELECT event_id
              FROM event_bus_outbox
             WHERE status IN ('pending', 'failed')
               AND next_attempt_at <= now()
             ORDER BY created_at ASC
             LIMIT $2
             FOR UPDATE SKIP LOCKED
          )
          RETURNING event_id, topic, signed_envelope, attempts`,
        [workerId, limit]
      );
      await client.query('COMMIT');

      let published = 0;
      let failed = 0;
      let deadLettered = 0;
      const producer = await getProducer();
      for (const record of claimed.rows) {
        try {
          await producer.send({
            topic: record.topic,
            messages: [{ key: record.event_id, value: JSON.stringify(record.signed_envelope) }],
          });
          await query(
            `UPDATE event_bus_outbox
                SET status = 'published',
                    published_at = now(),
                    locked_by = NULL,
                    locked_at = NULL,
                    last_error = NULL,
                    updated_at = now()
              WHERE event_id = $1`,
            [record.event_id]
          );
          published += 1;
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          const attempts = record.attempts + 1;
          if (attempts >= maxAttempts) {
            await this.deadLetterOutbox(record, attempts, message);
            deadLettered += 1;
          } else {
            await query(
              `UPDATE event_bus_outbox
                  SET status = 'failed',
                      attempts = $2,
                      next_attempt_at = now() + ($3::text || ' seconds')::interval,
                      locked_by = NULL,
                      locked_at = NULL,
                      last_error = $4,
                      updated_at = now()
                WHERE event_id = $1`,
              [record.event_id, attempts, Math.min(300, Math.pow(2, attempts)), message]
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

  async pendingOutboxCount(): Promise<number> {
    const rows = await query<{ count: string }>(
      `SELECT COUNT(*)::text AS count
         FROM event_bus_outbox
        WHERE status IN ('pending', 'failed', 'publishing')`
    );
    return Number(rows[0]?.count ?? 0);
  }

  private async deadLetterOutbox(record: EventBusOutboxRow, attempts: number, error: string): Promise<void> {
    const client = await db.connect();
    try {
      await client.query('BEGIN');
      await client.query(
        `UPDATE event_bus_outbox
            SET status = 'dead_lettered',
                attempts = $2,
                locked_by = NULL,
                locked_at = NULL,
                last_error = $3,
                updated_at = now()
          WHERE event_id = $1`,
        [record.event_id, attempts, error]
      );
      await client.query(
        `INSERT INTO event_bus_dead_letters (event_id, topic, signed_envelope, attempts, error)
         VALUES ($1,$2,$3::jsonb,$4,$5)
         ON CONFLICT (event_id) DO NOTHING`,
        [record.event_id, record.topic, JSON.stringify(record.signed_envelope), attempts, error]
      );
      await client.query('COMMIT');
    } catch (deadLetterError) {
      await client.query('ROLLBACK').catch(() => undefined);
      throw deadLetterError;
    } finally {
      client.release();
    }
  }
}

export const eventBus = new EventBusService();
