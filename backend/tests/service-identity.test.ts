import {
  assertProductionSecrets,
  authenticateRequest,
  hasScope,
  parseServiceKeys,
  Principal,
} from '../src/security';

function req(headers: Record<string, string>) {
  return { headers, url: '/test', method: 'POST' } as any;
}

describe('scoped service identity', () => {
  const env = {
    AGENTCO_SERVICE_KEYS_JSON: JSON.stringify({
      resolver: { key: 'resolver-key', scopes: ['prediction:resolve', 'evidence:write'] },
      credential: { key: 'credential-key', scopes: ['credential:issue', 'credential:verify'] },
      admin: { key: 'admin-key', scopes: ['admin:*', 'governance:*'] },
      auditor: { key: 'auditor-key', scopes: ['read:*', 'audit:read'] },
    }),
  } as NodeJS.ProcessEnv;

  test('parses service key config', () => {
    const parsed = parseServiceKeys(env);
    expect(parsed.resolver.scopes).toContain('prediction:resolve');
  });

  test('missing key rejected', () => {
    expect(authenticateRequest(req({}), env)).toBeUndefined();
  });

  test('wrong key rejected', () => {
    expect(authenticateRequest(req({ 'x-agentco-service-key': 'wrong' }), env)).toBeUndefined();
  });

  test('valid key accepted as principal', () => {
    const principal = authenticateRequest(req({ 'x-agentco-service-key': 'resolver-key' }), env);
    expect(principal!.principal_id).toBe('resolver');
    expect(principal!.auth_method).toBe('service_key');
  });

  test('scope and wildcard checks work', () => {
    const admin: Principal = { principal_id: 'admin', scopes: ['admin:*', 'governance:*'], auth_method: 'service_key' };
    expect(hasScope(admin, 'governance:mutate')).toBe(true);
    expect(hasScope(admin, 'credential:issue')).toBe(false);
  });

  test('auditor cannot mutate and resolver cannot issue credential', () => {
    const auditor: Principal = { principal_id: 'auditor', scopes: ['read:*', 'audit:read'], auth_method: 'service_key' };
    const resolver: Principal = { principal_id: 'resolver', scopes: ['prediction:resolve', 'evidence:write'], auth_method: 'service_key' };
    expect(hasScope(auditor, 'task:dispatch')).toBe(false);
    expect(hasScope(resolver, 'credential:issue')).toBe(false);
  });

  test('production without service keys fails startup guard', () => {
    expect(() => assertProductionSecrets({
      AGENTCO_ENV: 'production',
      AGENTCO_API_KEY: 'real-api-key',
      DATABASE_URL: 'postgresql://agentco:real-password@db:5432/agentco',
      EVENT_BUS_SIGNING_KEY: 'real-event-key',
      EVENT_BUS_HMAC_KEY: 'real-hmac-key',
      JWT_SECRET: 'real-jwt-secret',
      VAULT_TOKEN: 'real-vault-token',
      RESERVE_SIGNING_KEY: 'real-reserve-key',
    } as NodeJS.ProcessEnv)).toThrow(/AGENTCO_SERVICE_KEYS_JSON/);
  });

  test('dev fallback does not work in production', () => {
    const principal = authenticateRequest(
      req({ 'x-agentco-api-key': 'dev-api-key', 'x-agentco-role': 'operator' }),
      { AGENTCO_ENV: 'production' } as NodeJS.ProcessEnv,
    );
    expect(principal).toBeUndefined();
  });
});
