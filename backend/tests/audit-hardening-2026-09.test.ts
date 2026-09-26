/**
 * Regression tests for the 2026-09 full audit (docs/audit/FULL_AUDIT_2026-09.md).
 *   - SSRF guard: IPv6 forms that embed a private IPv4 (WHATWG URL parsing
 *     rewrites `[::ffff:127.0.0.1]` to `[::ffff:7f00:1]`) are rejected, and
 *     redirects are validated BEFORE the next hop is requested.
 *   - API preHandler: unauthenticated requests are rejected before learning
 *     capture runs, and bogus API keys cannot mint fresh rate-limit buckets.
 *   - Rate limiter memory is bounded.
 *   - The SSRF test escape hatch is refused in production-like envs.
 */

import http from 'http';
import type { AddressInfo } from 'net';
import { describe, expect, test, afterAll, beforeAll } from '@jest/globals';
import { assertPublicHttpUrl, isPrivateIp } from '../src/adapters/url-safety';
import { RealWebAdapter } from '../src/adapters/real-web-adapter';
import { RateLimitService, rateLimiterService } from '../src/services/rate-limiter.service';
import { learningService } from '../src/services/learning.service';
import { assertProductionSecrets } from '../src/security';
import { build } from '../src/server';

describe('SSRF guard: embedded-IPv4 IPv6 forms', () => {
  test.each([
    '::ffff:7f00:1', // ::ffff:127.0.0.1 as normalized by URL parsing
    '::ffff:a9fe:a9fe', // ::ffff:169.254.169.254 (cloud metadata)
    '::ffff:0a00:0001', // ::ffff:10.0.0.1
    '::ffff:127.0.0.1',
    '::7f00:1', // deprecated v4-compatible
    '64:ff9b::a9fe:a9fe', // NAT64
    '2002:7f00:1::', // 6to4 wrapping 127.0.0.1
    'ff02::1', // multicast
    'fec0::1', // site-local
  ])('%s is private', (ip) => {
    expect(isPrivateIp(ip)).toBe(true);
  });

  test.each(['2606:4700:4700::1111', '::ffff:808:808', '64:ff9b::808:808', '8.8.8.8'])('%s is public', (ip) => {
    expect(isPrivateIp(ip)).toBe(false);
  });

  test.each(['224.0.0.1', '240.0.0.1', '255.255.255.255', '198.18.0.1', '192.0.0.8'])('reserved IPv4 %s is private', (ip) => {
    expect(isPrivateIp(ip)).toBe(true);
  });

  test.each([
    'http://[::ffff:127.0.0.1]:3001/health',
    'http://[::ffff:169.254.169.254]/latest/meta-data',
    'http://[::ffff:a9fe:a9fe]/',
    'http://[64:ff9b::7f00:1]/',
  ])('assertPublicHttpUrl rejects %s', async (url) => {
    await expect(assertPublicHttpUrl(url)).rejects.toThrow(/private|reserved/);
  });
});

describe('SSRF guard: redirects are validated before they are followed', () => {
  let server: http.Server;
  let port: number;
  let internalHits = 0;
  const saved = process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;

  beforeAll(async () => {
    server = http.createServer((req, res) => {
      if (req.url === '/start') {
        // 127.0.0.2 is loopback but NOT in the allowLoopback literal list, so
        // it stands in for an internal-only address.
        res.writeHead(302, { location: `http://127.0.0.2:${port}/internal` });
        res.end();
        return;
      }
      if (req.url === '/internal') internalHits += 1;
      res.writeHead(200, { 'content-type': 'text/html' });
      res.end('<title>internal</title>secret');
    });
    await new Promise<void>((resolve) => server.listen(0, '0.0.0.0', resolve));
    port = (server.address() as AddressInfo).port;
    process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = '1';
  });

  afterAll(async () => {
    if (saved === undefined) delete process.env.AGENTCO_ALLOW_LOOPBACK_FETCH;
    else process.env.AGENTCO_ALLOW_LOOPBACK_FETCH = saved;
    await new Promise<void>((resolve) => server.close(() => resolve()));
  });

  test('redirect onto an internal address is never requested', async () => {
    const result = await new RealWebAdapter().fetch(`http://127.0.0.1:${port}/start`);
    expect(result).toBeNull();
    expect(internalHits).toBe(0);
  });
});

describe('API preHandler ordering and rate-limit identity', () => {
  const savedKey = process.env.AGENTCO_API_KEY;
  let app: Awaited<ReturnType<typeof build>>;

  beforeAll(async () => {
    process.env.AGENTCO_API_KEY = 'audit-hardening-test-key';
    rateLimiterService.resetAll();
    app = await build();
    await app.ready();
  });

  afterAll(async () => {
    await app.close();
    rateLimiterService.resetAll();
    if (savedKey === undefined) delete process.env.AGENTCO_API_KEY;
    else process.env.AGENTCO_API_KEY = savedKey;
  });

  test('unauthenticated requests never become learning signals', async () => {
    const before = learningService.getStats().total_signals;
    const res = await app.inject({
      method: 'POST',
      url: '/api/agents/attacker-chosen-agent/dispatch',
      headers: { 'x-api-key': 'wrong-key' },
      payload: { task_id: 'poison', agent_id: 'attacker-chosen-agent' },
    });
    expect(res.statusCode).toBe(401);
    expect(learningService.getStats().total_signals).toBe(before);
  });

  test('rotating bogus API keys shares one per-IP bucket', async () => {
    rateLimiterService.resetAll();
    const statuses: number[] = [];
    for (let i = 0; i < 105; i++) {
      const res = await app.inject({ method: 'GET', url: '/api/learning/stats', headers: { 'x-api-key': `bogus-${i}` } });
      statuses.push(res.statusCode);
    }
    expect(statuses.slice(0, 100).every((s) => s === 401)).toBe(true);
    expect(statuses.slice(100).every((s) => s === 429)).toBe(true);
    rateLimiterService.resetAll();
  });
});

describe('rate limiter memory is bounded', () => {
  test('distinct identifiers cannot grow the bucket map without limit', () => {
    const limiter = new RateLimitService();
    for (let i = 0; i < 12_000; i++) limiter.isAllowed(`id-${i}`, 'api');
    const size = (limiter as unknown as { buckets: Map<string, unknown> }).buckets.size;
    expect(size).toBeLessThanOrEqual(10_000);
    expect(limiter.isAllowed('id-11999', 'api')).toBe(true);
  });
});

describe('production secret posture', () => {
  test('the loopback-fetch test escape hatch is refused in production', () => {
    const env = {
      AGENTCO_ENV: 'production',
      AGENTCO_API_KEY: 'real-key',
      EVENT_BUS_SIGNING_KEY: 'k1',
      EVENT_BUS_HMAC_KEY: 'k2',
      JWT_SECRET: 'k3',
      VAULT_TOKEN: 'k4',
      AGENTCO_ALLOW_LOOPBACK_FETCH: '1',
    } as NodeJS.ProcessEnv;
    expect(() => assertProductionSecrets(env)).toThrow(/AGENTCO_ALLOW_LOOPBACK_FETCH/);
    expect(() => assertProductionSecrets({ ...env, AGENTCO_ALLOW_LOOPBACK_FETCH: undefined })).not.toThrow();
  });
});
