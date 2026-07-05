/**
 * API safety gates (E3-E5 / G11)
 * ==============================
 * The audit found: writes open by default, the rate limiter and input
 * validator existing as dead code, and a hardcoded dev service password.
 * These tests prove the wiring:
 *   - startup refuses key-less production and key-less non-loopback binds;
 *   - unauthenticated writes are rejected, authenticated ones pass;
 *   - the shared token-bucket rate limiter throttles every client;
 *   - the input validator blocks hostile fetch/search arguments in the
 *     executor (the runtime path, not just the service file);
 *   - the dev service-role password is refused in production (see also
 *     dsn-routing.test.ts).
 */

import crypto from 'crypto';
import { describe, expect, test, afterEach, beforeAll, afterAll } from '@jest/globals';
import { assertAuthPosture } from '../src/security';
import { rateLimiterService } from '../src/services/rate-limiter.service';
import { ActionExecutorService } from '../src/services/action-executor.service';
import { ActionSpec, ActionStatus, ActionType, RiskLevel } from '../src/types/action.types';
import { build } from '../src/server';

function withEnv<T>(overrides: Record<string, string | undefined>, fn: () => T): T {
  const saved: Record<string, string | undefined> = {};
  for (const key of Object.keys(overrides)) {
    saved[key] = process.env[key];
    if (overrides[key] === undefined) delete process.env[key];
    else process.env[key] = overrides[key];
  }
  try {
    return fn();
  } finally {
    for (const key of Object.keys(saved)) {
      if (saved[key] === undefined) delete process.env[key];
      else process.env[key] = saved[key];
    }
  }
}

describe('fail-closed auth posture (E3)', () => {
  test('production-like env without a real key refuses to start', () => {
    withEnv({ AGENTCO_ENV: 'production', AGENTCO_API_KEY: undefined }, () => {
      expect(() => assertAuthPosture('127.0.0.1')).toThrow(/AGENTCO_API_KEY/);
    });
    withEnv({ AGENTCO_ENV: 'production', AGENTCO_API_KEY: 'dev-api-key' }, () => {
      expect(() => assertAuthPosture('127.0.0.1')).toThrow(/AGENTCO_API_KEY/);
    });
  });

  test('non-loopback bind without a key refuses to start; loopback dev is allowed', () => {
    withEnv({ AGENTCO_ENV: undefined, NODE_ENV: 'test', AGENTCO_API_KEY: undefined }, () => {
      expect(() => assertAuthPosture('0.0.0.0')).toThrow(/non-loopback/);
      expect(() => assertAuthPosture('127.0.0.1')).not.toThrow();
    });
    withEnv({ AGENTCO_ENV: undefined, NODE_ENV: 'test', AGENTCO_API_KEY: 'real-key-123' }, () => {
      expect(() => assertAuthPosture('0.0.0.0')).not.toThrow();
    });
  });
});

describe('write auth + rate limiting on the live server (E3/E4)', () => {
  const API_KEY = `test-key-${crypto.randomUUID().slice(0, 8)}`;
  let app: Awaited<ReturnType<typeof build>>;
  const savedKey = process.env.AGENTCO_API_KEY;

  beforeAll(async () => {
    process.env.AGENTCO_API_KEY = API_KEY;
    app = await build();
  });

  afterAll(async () => {
    if (savedKey === undefined) delete process.env.AGENTCO_API_KEY;
    else process.env.AGENTCO_API_KEY = savedKey;
    await app.close();
  });

  afterEach(() => rateLimiterService.resetAll());

  test('unauthenticated writes are rejected; reads stay public', async () => {
    const write = await app.inject({ method: 'POST', url: '/api/agents', payload: {} });
    expect(write.statusCode).toBe(401);

    const read = await app.inject({ method: 'GET', url: '/health' });
    expect(read.statusCode).toBeLessThan(500);
    expect(read.statusCode).not.toBe(401);
  });

  test('authenticated writes pass the auth gate', async () => {
    const write = await app.inject({
      method: 'POST',
      url: '/api/agents',
      headers: { 'x-api-key': API_KEY },
      payload: {},
    });
    // Whatever the route thinks of the empty payload, auth must NOT be the
    // rejection: no 401/429.
    expect([401, 429]).not.toContain(write.statusCode);
  });

  test('the shared rate limiter throttles a client that exceeds its budget', async () => {
    let limited = 0;
    for (let i = 0; i < 130; i += 1) {
      const response = await app.inject({ method: 'GET', url: '/health' });
      if (response.statusCode === 429) limited += 1;
    }
    expect(limited).toBeGreaterThan(0);
  });
});

describe('input validator on the runtime action path (E4)', () => {
  function spec(actionType: ActionType, args: Record<string, unknown>): ActionSpec {
    return {
      actionId: crypto.randomUUID(),
      actionType,
      objective: 'input-validator test',
      args: args as any,
      successCriteria: [],
      riskLevel: RiskLevel.LOW,
      decidedBy: 'api-safety-gates-test',
      decidedAt: new Date(),
    } as unknown as ActionSpec;
  }

  test('hostile fetch URLs are blocked before any network activity', async () => {
    const executor = new ActionExecutorService();
    for (const url of ['javascript:alert(1)', 'file:///etc/passwd', `http://x.example/${'a'.repeat(3000)}`]) {
      const result = await executor.executeAction(spec(ActionType.FETCH_PAGE, { url }));
      expect(result.status).toBe(ActionStatus.BLOCKED);
      expect(result.blockedReason).toMatch(/rejected|Fetch/);
    }
  });

  test('hostile search queries are blocked', async () => {
    const executor = new ActionExecutorService();
    const result = await executor.executeAction(
      spec(ActionType.WEB_SEARCH, { query: 'find data javascript:stealCookies()' })
    );
    expect(result.status).toBe(ActionStatus.BLOCKED);
    expect(result.blockedReason).toMatch(/suspicious|rejected/);
  });
});
