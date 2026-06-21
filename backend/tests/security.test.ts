import { build } from '../src/server';
import { assertProductionSecrets } from '../src/security';

describe('production secret guard', () => {
  test('fails closed in production with dev defaults', () => {
    expect(() => assertProductionSecrets({
      AGENTCO_ENV: 'production',
      AGENTCO_API_KEY: 'dev-api-key',
      DATABASE_URL: 'postgresql://agentco:password@localhost:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'dev-key-replace-in-production',
      EVENT_BUS_HMAC_KEY: 'dev-insecure-key',
      JWT_SECRET: 'change-me-generate-with-openssl-rand-hex-64',
      VAULT_TOKEN: 'root',
    } as NodeJS.ProcessEnv)).toThrow(/Refusing to start in production/);
  });

  test('allows production with non-default required secrets', () => {
    expect(() => assertProductionSecrets({
      AGENTCO_ENV: 'production',
      AGENTCO_API_KEY: 'real-api-key',
      DATABASE_URL: 'postgresql://agentco:real-password@db:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'real-event-signing-key',
      EVENT_BUS_HMAC_KEY: 'real-hmac-key',
      JWT_SECRET: 'real-jwt-secret',
      VAULT_TOKEN: 'real-vault-token',
      RESERVE_SIGNING_KEY: 'real-reserve-key',
      AGENTCO_SERVICE_KEYS_JSON: '{"admin":{"key":"real-service-key","scopes":["admin:*"]}}',
    } as NodeJS.ProcessEnv)).not.toThrow();
  });
});

describe('minimal API key auth', () => {
  test('rejects write endpoint without x-agentco-api-key before handler work', async () => {
    const app = await build();
    const res = await app.inject({
      method: 'POST',
      url: '/api/overrides',
      payload: { agent_id: 'test', action: 'x', risk_level: 'high', context: {} },
    });
    expect(res.statusCode).toBe(401);
    await app.close();
  });

  test('read endpoint remains open', async () => {
    const app = await build();
    const res = await app.inject({ method: 'GET', url: '/health' });
    expect(res.statusCode).toBe(200);
    await app.close();
  });
});
