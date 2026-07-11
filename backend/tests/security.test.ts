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
      LLM_API_KEY: 'real-llm-key',
      LLM_BUDGET_ENFORCEMENT: 'required',
      LLM_RESOURCE_ACTOR_ID: '11111111-1111-4111-8111-111111111111',
      LLM_RESOURCE_ACCOUNT_ID: '22222222-2222-4222-8222-222222222222',
    } as NodeJS.ProcessEnv)).not.toThrow();
  });

  test('rejects production LLM credentials without durable budget wiring', () => {
    expect(() => assertProductionSecrets({
      AGENTCO_ENV: 'production',
      AGENTCO_API_KEY: 'real-api-key',
      DATABASE_URL: 'postgresql://agentco:real-password@db:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'real-event-signing-key',
      EVENT_BUS_HMAC_KEY: 'real-hmac-key',
      JWT_SECRET: 'real-jwt-secret',
      VAULT_TOKEN: 'real-vault-token',
      RESERVE_SIGNING_KEY: 'real-reserve-key',
      LLM_API_KEY: 'real-llm-key',
    } as NodeJS.ProcessEnv)).toThrow(/LLM_RESOURCE_ACTOR_ID/);
  });

  test('treats NODE_ENV=production as production even without AGENTCO_ENV', () => {
    expect(() => assertProductionSecrets({
      NODE_ENV: 'production',
      AGENTCO_API_KEY: 'dev-api-key',
      DATABASE_URL: 'postgresql://agentco:password@localhost:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'dev-key-replace-in-production',
      EVENT_BUS_HMAC_KEY: 'dev-insecure-key',
      JWT_SECRET: 'change-me-generate-with-openssl-rand-hex-64',
      VAULT_TOKEN: 'root',
    } as NodeJS.ProcessEnv)).toThrow(/Refusing to start in production/);
  });

  test('treats AGENTCO_ENV=staging as production-like', () => {
    expect(() => assertProductionSecrets({
      AGENTCO_ENV: 'staging',
      AGENTCO_API_KEY: 'dev-api-key',
      DATABASE_URL: 'postgresql://agentco:password@localhost:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'dev-key-replace-in-production',
      EVENT_BUS_HMAC_KEY: 'dev-insecure-key',
      JWT_SECRET: 'change-me-generate-with-openssl-rand-hex-64',
      VAULT_TOKEN: 'root',
    } as NodeJS.ProcessEnv)).toThrow(/Refusing to start in production/);
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
