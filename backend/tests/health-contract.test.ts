jest.mock('../src/db/client', () => ({
  db: {
    query: jest.fn(),
  },
}));

jest.mock('../src/db/kafka', () => ({
  checkKafkaHealth: jest.fn(),
}));

import fs from 'fs';
import path from 'path';
import { build } from '../src/server';
import { db } from '../src/db/client';
import { checkKafkaHealth } from '../src/db/kafka';

const mockedDbQuery = db.query as jest.Mock;
const mockedKafkaHealth = checkKafkaHealth as jest.MockedFunction<typeof checkKafkaHealth>;

describe('health and readiness contract', () => {
  const savedKafka = process.env.KAFKA_BROKERS;
  const savedMandatory = process.env.KAFKA_MANDATORY;

  afterEach(() => {
    jest.resetAllMocks();
    if (savedKafka === undefined) delete process.env.KAFKA_BROKERS;
    else process.env.KAFKA_BROKERS = savedKafka;
    if (savedMandatory === undefined) delete process.env.KAFKA_MANDATORY;
    else process.env.KAFKA_MANDATORY = savedMandatory;
  });

  test('liveness is public and succeeds when dependencies are unavailable', async () => {
    mockedDbQuery.mockRejectedValue(new Error('connection refused'));
    const app = await build();
    const response = await app.inject({ method: 'GET', url: '/health/live' });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual(expect.objectContaining({ status: 'ok', request_id: expect.any(String) }));
    await app.close();
  });

  test('readiness fails with sanitized dependency detail when a mandatory dependency is unavailable', async () => {
    mockedDbQuery.mockRejectedValue(new Error('postgresql://user:secret@db connection refused'));
    const app = await build();
    const response = await app.inject({ method: 'GET', url: '/health/ready' });
    expect(response.statusCode).toBe(503);
    expect(response.body).not.toContain('secret');
    expect(response.json()).toEqual(expect.objectContaining({
      status: 'not_ready',
      dependencies: expect.objectContaining({
        database: expect.objectContaining({ status: 'unhealthy', mandatory: true }),
      }),
    }));
    await app.close();
  });

  test('readiness succeeds when mandatory dependencies are healthy', async () => {
    mockedDbQuery.mockResolvedValue({ rows: [{ ok: 1 }] });
    delete process.env.KAFKA_BROKERS;
    const app = await build();
    const response = await app.inject({ method: 'GET', url: '/health/ready' });
    expect(response.statusCode).toBe(200);
    expect(response.json()).toEqual(expect.objectContaining({
      status: 'ready',
      dependencies: expect.objectContaining({
        database: expect.objectContaining({ status: 'healthy' }),
        kafka: expect.objectContaining({ status: 'disabled', mandatory: false }),
      }),
    }));
    await app.close();
  });

  test('mandatory Kafka health contacts the broker and gates readiness', async () => {
    mockedDbQuery.mockResolvedValue({ rows: [{ ok: 1 }] });
    mockedKafkaHealth.mockRejectedValue(new Error('broker unavailable'));
    process.env.KAFKA_BROKERS = 'kafka:9092';
    process.env.KAFKA_MANDATORY = 'true';
    const app = await build();
    const response = await app.inject({ method: 'GET', url: '/health/ready' });
    expect(mockedKafkaHealth).toHaveBeenCalledTimes(1);
    expect(response.statusCode).toBe(503);
    expect(response.json().dependencies.kafka).toEqual(expect.objectContaining({
      status: 'unhealthy',
      mandatory: true,
    }));
    await app.close();
  });

  test('Helm-rendered probe values reference implemented backend endpoints', () => {
    const values = fs.readFileSync(
      path.resolve(__dirname, '../../infrastructure/kubernetes/helm/agentco/values.yaml'),
      'utf8'
    );
    expect(values).toContain('path: /health/live');
    expect(values).toContain('path: /health/ready');
  });

  test('Helm backend deployment wires required production secret references', () => {
    const deployment = fs.readFileSync(
      path.resolve(__dirname, '../../infrastructure/kubernetes/helm/agentco/templates/deployment.yaml'),
      'utf8'
    );
    for (const key of [
      'AGENTCO_API_KEY',
      'EVENT_BUS_SIGNING_KEY',
      'EVENT_BUS_HMAC_KEY',
      'JWT_SECRET',
      'DATABASE_URL',
      'REDIS_URL',
      'KAFKA_BROKERS',
      'LLM_API_KEY',
      'VAULT_TOKEN',
      'RESERVE_SIGNING_KEY',
    ]) {
      expect(deployment).toContain(`key: ${key}`);
    }
  });
});
