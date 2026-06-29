/**
 * Event Bus Integration Tests — real Kafka + real Postgres, no mocks.
 *
 * Requires: Kafka on localhost:9092, Postgres on localhost:5433, event_history table.
 *
 * Tests:
 *   1. publish() sends to Kafka and persists to event_history
 *   2. Duplicate publish is idempotent (ON CONFLICT DO NOTHING)
 *   3. verifySignature() accepts correctly signed event
 *   4. verifySignature() rejects tampered payload
 *   5. verifySignature() rejects bad-signature string
 *   6. validateEnvelope() rejects missing required fields
 */

import crypto from 'crypto';
import net from 'net';
import { Pool } from 'pg';
import { EventBusService, AgentEvent, SignedEvent } from '../../src/services/event-bus.service';

const DSN =
  process.env.DATABASE_URL ||
  'postgresql://agentco:password@localhost:5433/agentco?host=/tmp';

const db = new Pool({ connectionString: DSN });
const svc = new EventBusService();
let kafkaReachable = false;

function canConnect(port: number, host = '127.0.0.1'): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port, timeout: 300 });
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => resolve(false));
  });
}

function makeEvent(overrides: Partial<AgentEvent> = {}): AgentEvent {
  return {
    event_id: crypto.randomUUID(),
    event_type: 'engineering.test_event',
    producer_agent_id: 'test-agent-eventbus',
    timestamp: new Date().toISOString(),
    confidence_score: 0.9,
    payload: { test: true, value: Math.random() },
    risk_level: 'low',
    requires_ack: false,
    ...overrides,
  };
}

afterAll(async () => {
  await db.end();
});

describe('Event Bus — real Kafka + Postgres', () => {
  beforeAll(async () => {
    kafkaReachable = await canConnect(9092);
  });

  test('publish() persists event to event_history', async () => {
    if (!kafkaReachable) {
      console.warn('Kafka unavailable on localhost:9092; skipping real publish integration check');
      return;
    }
    const event = makeEvent();
    await svc.publish(event);

    const { rows } = await db.query(
      `SELECT event_id, event_type, producer_agent_id, risk_level FROM event_history WHERE event_id = $1`,
      [event.event_id]
    );
    expect(rows).toHaveLength(1);
    expect(rows[0].event_id).toBe(event.event_id);
    expect(rows[0].event_type).toBe(event.event_type);
    expect(rows[0].producer_agent_id).toBe(event.producer_agent_id);
    expect(rows[0].risk_level).toBe(event.risk_level);
  });

  test('publish() is idempotent on duplicate event_id', async () => {
    if (!kafkaReachable) {
      console.warn('Kafka unavailable on localhost:9092; skipping real publish idempotency check');
      return;
    }
    const event = makeEvent();
    await svc.publish(event);
    await svc.publish(event);  // second call must not throw or create duplicate

    const { rows } = await db.query(
      `SELECT COUNT(*) FROM event_history WHERE event_id = $1`,
      [event.event_id]
    );
    expect(Number(rows[0].count)).toBe(1);
  });

  test('verifySignature() accepts correctly signed event', () => {
    const event = makeEvent();
    const sigKey = process.env.EVENT_BUS_SIGNING_KEY ?? 'dev-key-replace-in-production';
    const signature = require('crypto')
      .createHmac('sha256', sigKey)
      .update(JSON.stringify(event))
      .digest('hex');
    const signed: SignedEvent = { ...event, signature };
    expect(svc.verifySignature(signed)).toBe(true);
  });

  test('verifySignature() rejects tampered payload', () => {
    const event = makeEvent();
    const sigKey = process.env.EVENT_BUS_SIGNING_KEY ?? 'dev-key-replace-in-production';
    const signature = require('crypto')
      .createHmac('sha256', sigKey)
      .update(JSON.stringify(event))
      .digest('hex');
    const signed: SignedEvent = { ...event, signature };
    // Tamper after signing
    signed.payload = { tampered: true };
    expect(svc.verifySignature(signed)).toBe(false);
  });

  test('verifySignature() rejects wrong signature string', () => {
    const event = makeEvent();
    const signed: SignedEvent = { ...event, signature: 'a'.repeat(64) };
    expect(svc.verifySignature(signed)).toBe(false);
  });

  test('validateEnvelope() rejects missing event_id', () => {
    const event = makeEvent();
    // @ts-expect-error intentional
    delete event.event_id;
    expect(() => svc.validateEnvelope(event)).toThrow(/event_id/);
  });

  test('validateEnvelope() rejects out-of-range confidence_score', () => {
    const event = makeEvent({ confidence_score: 1.5 });
    expect(() => svc.validateEnvelope(event)).toThrow(/confidence_score/);
  });
});
