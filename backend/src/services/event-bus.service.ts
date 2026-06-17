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
import { query } from '../db/client';
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

    // 1. Produce to Kafka
    const producer = await getProducer();
    await producer.send({
      topic,
      messages: [{ key: event.event_id, value: JSON.stringify(signed) }],
    });

    // 2. Persist to event_history (append-only, idempotent)
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

    // 3. Audit the publish
    await auditLog.append({
      agent_id: event.producer_agent_id,
      action_type: 'event_published',
      input_summary: `event_type=${event.event_type} topic=${topic}`,
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
}

export const eventBus = new EventBusService();
