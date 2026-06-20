import { build } from '../src/server';
import { assertProductionSecrets } from '../src/security';

const key = 'dev-api-key';
const headers = (role: string) => ({ 'x-agentco-api-key': key, 'x-agentco-role': role });

describe('RBAC and scoped service identity', () => {
  test('unauthenticated write rejected', async () => {
    const app = await build();
    const res = await app.inject({ method: 'POST', url: '/claims/register', payload: { claim: 'x' } });
    expect(res.statusCode).toBe(401);
    await app.close();
  });

  test('wrong role rejected and correct role allowed', async () => {
    const app = await build();
    const wrong = await app.inject({
      method: 'POST',
      url: '/claims/register',
      headers: headers('auditor'),
      payload: { claim: 'x' },
    });
    expect(wrong.statusCode).toBe(403);
    const correct = await app.inject({
      method: 'POST',
      url: '/claims/register',
      headers: headers('agent'),
      payload: { claim: 'x', producing_agent_id: 'agent-1' },
    });
    expect(correct.statusCode).toBe(201);
    await app.close();
  });

  test('agent cannot resolve own claim', async () => {
    const app = await build();
    const registered = await app.inject({
      method: 'POST',
      url: '/claims/register',
      headers: headers('agent'),
      payload: { claim: 'x', producing_agent_id: 'agent-1' },
    });
    const id = JSON.parse(registered.payload).id;
    const resolved = await app.inject({
      method: 'POST',
      url: `/claims/${id}/resolve`,
      headers: headers('resolver_service'),
      payload: { resolver_id: 'agent-1' },
    });
    expect(resolved.statusCode).toBe(403);
    await app.close();
  });

  test('resolver cannot issue credential and reserve issuer cannot mutate source ledger', async () => {
    const app = await build();
    const resolverIssue = await app.inject({
      method: 'POST',
      url: '/credentials/issue',
      headers: headers('resolver_service'),
      payload: { agent_id: 'agent-1' },
    });
    expect(resolverIssue.statusCode).toBe(403);
    const issuerClaim = await app.inject({
      method: 'POST',
      url: '/claims/register',
      headers: headers('reserve_issuer'),
      payload: { claim: 'x' },
    });
    expect(issuerClaim.statusCode).toBe(403);
    await app.close();
  });

  test('auditor cannot mutate and privileged rejection logged', async () => {
    const app = await build();
    const rejected = await app.inject({
      method: 'POST',
      url: '/institutions',
      headers: headers('auditor'),
      payload: { name: 'Nope' },
    });
    expect(rejected.statusCode).toBe(403);
    const audit = await app.inject({ method: 'GET', url: '/audit/security' });
    expect(JSON.parse(audit.payload).events.some((e: { reason: string }) => e.reason.includes('missing_scope'))).toBe(true);
    await app.close();
  });

  test('dev secrets rejected in production', () => {
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
});
