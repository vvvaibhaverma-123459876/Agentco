/**
 * DSN routing regression (G1)
 * ===========================
 * The split-brain bug: with BOTH DATABASE_URL and AGENTCO_TEST_DATABASE_URL
 * set, prediction writes went to one database while the resolution firewall
 * connected to another, and the flagship autonomy CLI died with
 * "unresolved prediction not found".
 *
 * This suite pins the fix at three levels:
 *   1. precedence — one documented order, applied by the shared resolver;
 *   2. exclusivity — no src/ module besides db/dsn.ts builds its own DSN
 *      from those env vars, so the precedence cannot fork again;
 *   3. behavior — a prediction registered through the app pool resolves
 *      through the firewall pool derived by the same resolver.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { Pool } from 'pg';
import { describe, expect, test, afterAll } from '@jest/globals';
import { appDatabaseUrl, resolutionServiceDatabaseUrl } from '../src/db/dsn';
import { ledgerResolutionService } from '../src/services/resolution-service.service';

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

describe('shared DSN resolver (G1)', () => {
  test('DATABASE_URL wins when both env vars are set, and the firewall DSN derives from the SAME base', () => {
    withEnv(
      {
        DATABASE_URL: 'postgresql://app:pw@db-one:5432/one',
        AGENTCO_TEST_DATABASE_URL: 'postgresql://app:pw@db-two:5432/two',
        RESOLUTION_SERVICE_DATABASE_URL: undefined,
        RESOLUTION_SERVICE_PASSWORD: 'svc-pw',
      },
      () => {
        expect(appDatabaseUrl()).toBe('postgresql://app:pw@db-one:5432/one');
        const svc = new URL(resolutionServiceDatabaseUrl());
        // Same host and database as the app DSN — never db-two.
        expect(svc.hostname).toBe('db-one');
        expect(svc.pathname).toBe('/one');
        expect(svc.username).toBe('resolution_service');
      }
    );
  });

  test('explicit RESOLUTION_SERVICE_DATABASE_URL still overrides for split deployments', () => {
    withEnv(
      { RESOLUTION_SERVICE_DATABASE_URL: 'postgresql://resolution_service:x@fw:5432/one' },
      () => {
        expect(resolutionServiceDatabaseUrl()).toBe('postgresql://resolution_service:x@fw:5432/one');
      }
    );
  });

  test('dev service password is refused in production/staging (G11)', () => {
    withEnv(
      { AGENTCO_ENV: 'production', RESOLUTION_SERVICE_PASSWORD: undefined },
      () => {
        expect(() => resolutionServiceDatabaseUrl()).toThrow(/RESOLUTION_SERVICE_PASSWORD/);
      }
    );
  });

  test('no src/ module besides db/dsn.ts re-implements DSN env precedence', () => {
    const srcRoot = path.resolve(__dirname, '../src');
    const offenders: string[] = [];
    const walk = (dir: string): void => {
      for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
        const full = path.join(dir, entry.name);
        if (entry.isDirectory()) walk(full);
        else if (entry.name.endsWith('.ts')) {
          const text = fs.readFileSync(full, 'utf8');
          const rel = path.relative(srcRoot, full);
          if (rel === path.join('db', 'dsn.ts')) continue;
          // security.ts only inspects env values for dev-password posture; it
          // must not CONSTRUCT connection strings from them.
          for (const line of text.split('\n')) {
            const code = line.split('//')[0];
            if (/process\.env\.AGENTCO_TEST_DATABASE_URL\s*\?\?|new URL\(process\.env\.(DATABASE_URL|AGENTCO_TEST_DATABASE_URL)/.test(code)) {
              offenders.push(rel);
            }
          }
        }
      }
    };
    walk(srcRoot);
    expect(offenders).toEqual([]);
  });
});

describe('same-database round-trip through the resolver (G1)', () => {
  let servicePool: Pool | null = null;
  afterAll(async () => {
    if (servicePool) await servicePool.end();
  });

  test('a prediction registered via the app pool resolves via the derived firewall pool', async () => {
    const predictionId = await ledgerResolutionService.registerPrediction({
      claim: 'dsn-routing regression: writer and resolver share one database',
      probability: 0.6,
      confidence_basis: { test: 'dsn-routing' },
      producing_agent_id: `dsn-routing-${crypto.randomUUID()}`,
      producing_prompt_version: 'dsn-routing-v1',
      resolution_criterion: 'resolved by this regression test',
      resolution_date: new Date(Date.now() - 1000),
      ground_truth_source: 'agentco://tests/dsn-routing',
      horizon_class: 'short',
      domain: 'test_dsn_routing',
      historical_registration_reason: 'deterministic dsn-routing fixture',
    });

    servicePool = new Pool({ connectionString: resolutionServiceDatabaseUrl(), max: 2 });
    const client = await servicePool.connect();
    try {
      const record = await ledgerResolutionService.resolveWithClient(client, {
        prediction_id: predictionId,
        resolved_outcome: false,
      });
      expect(record.resolved).toBe(true);
      expect(record.resolved_outcome).toBe(false);
    } finally {
      client.release();
    }
  });
});
