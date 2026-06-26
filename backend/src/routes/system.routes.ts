import { FastifyInstance } from 'fastify';
import fs from 'fs';
import path from 'path';
import YAML from 'yaml';
import { RuntimeProvider, activeRuntimeMode, configuredProviders } from '../runtime-mode';
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

function fallbackProviders(providers: RuntimeProvider[]) {
  return providers.filter(provider => provider.status === 'fallback' || provider.status === 'simulated');
}

function disabledCapabilities(providers: RuntimeProvider[]) {
  return providers.filter(provider => provider.status === 'unsupported').map(provider => provider.name);
}

function readinessVerdict(ledgerSummary: ReturnType<typeof summarizeLedger>, providers: RuntimeProvider[]) {
  const fallbackActive = fallbackProviders(providers).length > 0;
  const disabled = disabledCapabilities(providers);
  const terminationMet = ledgerSummary.meta?.termination_predicate_met === true;
  const percentVerified = ledgerSummary.rollups.percent_verified;

  if (activeRuntimeMode() === 'production' && (fallbackActive || disabled.length > 0 || !terminationMet)) {
    return 'not_production_ready';
  }
  if (!terminationMet || percentVerified < 100) {
    return fallbackActive || disabled.length > 0 ? 'partial_with_fallbacks' : 'partial';
  }
  return fallbackActive ? 'runnable_with_fallbacks' : 'ready';
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
      fallback_active: fallbackProviders(providers).length > 0,
      disabled_capabilities: disabledCapabilities(providers),
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

  fastify.get('/system/readiness', async () => {
    const providers = configuredProviders();
    const ledger = summarizeLedger(loadBuildLedger());
    const fallbacks = fallbackProviders(providers);
    const disabled = disabledCapabilities(providers);
    return {
      verdict: readinessVerdict(ledger, providers),
      runtime_mode: activeRuntimeMode(),
      can_continue: disabled.length === 0,
      production_ready: readinessVerdict(ledger, providers) === 'ready' && activeRuntimeMode() === 'production',
      fallback_active: fallbacks.length > 0,
      fallbacks,
      disabled_capabilities: disabled,
      build_ledger: ledger.rollups,
      termination_predicate_met: ledger.meta?.termination_predicate_met === true,
      honesty: {
        verified_items: ledger.rollups.verified,
        total_items: ledger.rollups.total_items,
        percent_verified: ledger.rollups.percent_verified,
        status: ledger.rollups.percent_verified === 100 ? 'fully_verified' : 'not_fully_verified',
      },
    };
  });
}
