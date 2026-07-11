jest.mock('../src/db/client', () => ({
  db: {
    connect: jest.fn(),
  },
  query: jest.fn(),
}));

jest.mock('../src/db/kafka', () => ({
  getProducer: jest.fn(),
  createConsumer: jest.fn(),
}));

jest.mock('../src/services/audit-log.service', () => ({
  auditLog: {
    append: jest.fn().mockResolvedValue({ log_id: 'audit-log-id' }),
  },
}));

import { db, query } from '../src/db/client';
import { getProducer } from '../src/db/kafka';
import { auditLog } from '../src/services/audit-log.service';
import { EventBusService, AgentEvent } from '../src/services/event-bus.service';

const mockedConnect = db.connect as jest.Mock;
const mockedQuery = query as jest.Mock;
const mockedGetProducer = getProducer as jest.Mock;
const mockedAuditAppend = auditLog.append as jest.Mock;

function makeEvent(): AgentEvent {
  return {
    event_id: '11111111-1111-4111-8111-111111111111',
    event_type: 'engineering.test_event',
    producer_agent_id: 'test-agent',
    timestamp: '2026-07-11T00:00:00.000Z',
    confidence_score: 0.9,
    payload: { ok: true },
    correlation_id: '22222222-2222-4222-8222-222222222222',
    risk_level: 'low',
    requires_ack: false,
  };
}

function mockClient(rows: unknown[] = []) {
  const client = {
    query: jest.fn()
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValueOnce({ rows })
      .mockResolvedValueOnce({ rows: [] })
      .mockResolvedValue({ rows: [] }),
    release: jest.fn(),
  };
  mockedConnect.mockResolvedValue(client);
  return client;
}

describe('EventBusService durable outbox mode', () => {
  const savedEnv = { ...process.env };

  beforeEach(() => {
    jest.clearAllMocks();
    process.env = { ...savedEnv };
    process.env.AGENTCO_ENV = 'production';
    process.env.EVENT_BUS_SIGNING_KEY = 'test-signing-key';
  });

  afterEach(() => {
    process.env = savedEnv;
  });

  test('production publish schedules event_history and outbox atomically without touching Kafka', async () => {
    const client = mockClient();
    await new EventBusService().publish(makeEvent());

    expect(mockedGetProducer).not.toHaveBeenCalled();
    expect(client.query).toHaveBeenCalledWith('BEGIN');
    expect(client.query.mock.calls.some(call => String(call[0]).includes('INSERT INTO event_history'))).toBe(true);
    expect(client.query.mock.calls.some(call => String(call[0]).includes('INSERT INTO event_bus_outbox'))).toBe(true);
    expect(client.query).toHaveBeenCalledWith('COMMIT');
    expect(client.release).toHaveBeenCalled();
    expect(mockedAuditAppend).toHaveBeenCalledWith(expect.objectContaining({
      input_summary: expect.stringContaining('delivery=scheduled'),
    }));
  });

  test('sync mode still sends to Kafka then persists history for local compatibility', async () => {
    process.env.AGENTCO_ENV = 'development';
    process.env.EVENT_BUS_DELIVERY_MODE = 'sync';
    const send = jest.fn().mockResolvedValue(undefined);
    mockedGetProducer.mockResolvedValue({ send });
    mockedQuery.mockResolvedValue([]);

    await new EventBusService().publish(makeEvent());

    expect(send).toHaveBeenCalledWith(expect.objectContaining({
      topic: 'agentco.engineering',
      messages: [expect.objectContaining({ key: makeEvent().event_id })],
    }));
    expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining('INSERT INTO event_history'), expect.any(Array));
  });

  test('relayOutboxBatch publishes claimed rows and marks them published', async () => {
    const event = makeEvent();
    const client = mockClient([{
      event_id: event.event_id,
      topic: 'agentco.engineering',
      signed_envelope: { ...event, signature: 'a'.repeat(64) },
      attempts: 0,
    }]);
    const send = jest.fn().mockResolvedValue(undefined);
    mockedGetProducer.mockResolvedValue({ send });
    mockedQuery.mockResolvedValue([]);

    const result = await new EventBusService().relayOutboxBatch({ limit: 1, maxAttempts: 2 });

    expect(client.query.mock.calls.some(call => String(call[0]).includes('UPDATE event_bus_outbox'))).toBe(true);
    expect(send).toHaveBeenCalledWith(expect.objectContaining({
      topic: 'agentco.engineering',
      messages: [expect.objectContaining({ key: event.event_id })],
    }));
    expect(mockedQuery).toHaveBeenCalledWith(expect.stringContaining("SET status = 'published'"), [event.event_id]);
    expect(result).toEqual({ published: 1, failed: 0, dead_lettered: 0 });
  });
});
