import { FastifyInstance } from 'fastify';
import fs from 'fs';
import path from 'path';
import YAML from 'yaml';
import { activeRuntimeMode, configuredProviders } from '../runtime-mode';
import { db } from '../db/client';

function repoRoot(): string {
  return path.resolve(__dirname, '../../../');
}

function loadBuildLedger(): any {
  const ledgerPath = path.join(repoRoot(), 'BUILD_LEDGER.yaml');
  const text = fs.readFileSync(ledgerPath, 'utf8');
  return YAML.parse(text);
}

function summarizeLedger(ledger: any) {
  const items = Object.values(ledger.layers || {}).flatMap((layer: any) => layer.items || []);
  const counts = items.reduce((acc: Record<string, number>, item: any) => {
    acc[item.status] = (acc[item.status] || 0) + 1;
    return acc;
  }, {});
  const total = items.length;
  const verified = counts.verified || 0;
  return {
    meta: ledger.meta,
    rollups: {
      total_items: total,
      verified,
      in_progress: counts.in_progress || 0,
      not_started: counts.not_started || 0,
      blocked: counts.blocked || 0,
      percent_verified: total > 0 ? Math.round((verified / total) * 10000) / 100 : 0,
    },
    gates: ledger.gates,
  };
}

export async function systemRoutes(fastify: FastifyInstance) {
  fastify.get('/system/health', async () => ({
    status: 'ok',
    runtime_mode: activeRuntimeMode(),
    timestamp: new Date().toISOString(),
  }));

  fastify.get('/system/runtime-mode', async () => ({
    runtime_mode: activeRuntimeMode(),
  }));

  fastify.get('/system/capabilities', async () => {
    const providers = configuredProviders();
    return {
      runtime_mode: activeRuntimeMode(),
      providers,
      can_continue: !providers.some(provider => provider.status === 'unsupported'),
      fallback_active: providers.some(provider => provider.status === 'fallback' || provider.status === 'simulated'),
      disabled_capabilities: providers.filter(provider => provider.status === 'unsupported').map(provider => provider.name),
    };
  });

  fastify.get('/system/fallbacks', async () => ({
    runtime_mode: activeRuntimeMode(),
    fallbacks: configuredProviders().filter(provider => provider.status === 'fallback' || provider.status === 'simulated'),
  }));

  fastify.get('/system/version', async () => {
    const pkg = JSON.parse(fs.readFileSync(path.join(repoRoot(), 'backend/package.json'), 'utf8'));
    return {
      name: pkg.name,
      version: pkg.version,
      git_commit: process.env.GIT_COMMIT || null,
    };
  });

  fastify.get('/system/migrations', async (_request, reply) => {
    try {
      const result = await db.query(
        'SELECT filename, applied_at FROM schema_migrations ORDER BY filename DESC LIMIT 25'
      );
      return {
        status: 'real',
        count: result.rowCount,
        latest: result.rows,
      };
    } catch (error) {
      return reply.status(503).send({
        status: 'blocked',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  });

  fastify.get('/system/build-status', async () => summarizeLedger(loadBuildLedger()));
}
