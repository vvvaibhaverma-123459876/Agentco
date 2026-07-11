import { db } from './db/client';
import { checkKafkaHealth } from './db/kafka';
import { activeRuntimeMode, configuredProviders } from './runtime-mode';

export interface DependencyCheck {
  status: 'healthy' | 'unhealthy' | 'disabled';
  mandatory: boolean;
  latency_ms?: number;
  error?: string;
}

export interface HealthReport {
  status: 'ok' | 'ready' | 'not_ready' | 'degraded';
  request_id: string;
  timestamp: string;
  dependencies: Record<string, DependencyCheck>;
}

function boolEnv(name: string, defaultValue = false): boolean {
  const raw = process.env[name];
  if (raw === undefined) return defaultValue;
  return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

async function withTimeout<T>(label: string, ms: number, fn: () => Promise<T>): Promise<T> {
  let timeout: NodeJS.Timeout | undefined;
  try {
    return await Promise.race([
      fn(),
      new Promise<never>((_, reject) => {
        timeout = setTimeout(() => reject(new Error(`${label} timeout`)), ms);
      }),
    ]);
  } finally {
    if (timeout) clearTimeout(timeout);
  }
}

function sanitizedError(error: unknown): string {
  if (!(error instanceof Error)) return 'unknown_error';
  const msg = error.message.toLowerCase();
  if (msg.includes('timeout')) return 'timeout';
  if (msg.includes('authentication') || msg.includes('password')) return 'authentication_failed';
  if (msg.includes('connection') || msg.includes('econnrefused') || msg.includes('enotfound')) return 'connection_failed';
  return 'dependency_check_failed';
}

export function processHealth(requestId: string) {
  return {
    status: 'ok',
    request_id: requestId,
    timestamp: new Date().toISOString(),
    runtime_mode: activeRuntimeMode(),
  };
}

export async function dependencyHealthReport(requestId: string): Promise<HealthReport> {
  const timeoutMs = Number(process.env.HEALTH_CHECK_TIMEOUT_MS ?? 1500);
  const kafkaMandatory = boolEnv('KAFKA_MANDATORY', activeRuntimeMode() === 'production');
  const dependencies: Record<string, DependencyCheck> = {};

  const dbStart = Date.now();
  try {
    await withTimeout('database', timeoutMs, async () => {
      const result = await db.query('SELECT 1 AS ok');
      if (!result.rows.length) throw new Error('database returned no rows');
    });
    dependencies.database = { status: 'healthy', mandatory: true, latency_ms: Date.now() - dbStart };
  } catch (error) {
    dependencies.database = {
      status: 'unhealthy',
      mandatory: true,
      latency_ms: Date.now() - dbStart,
      error: sanitizedError(error),
    };
  }

  if (process.env.KAFKA_BROKERS) {
    const kafkaStart = Date.now();
    try {
      await withTimeout('kafka', timeoutMs, () => checkKafkaHealth());
      dependencies.kafka = { status: 'healthy', mandatory: kafkaMandatory, latency_ms: Date.now() - kafkaStart };
    } catch (error) {
      dependencies.kafka = {
        status: 'unhealthy',
        mandatory: kafkaMandatory,
        latency_ms: Date.now() - kafkaStart,
        error: sanitizedError(error),
      };
    }
  } else {
    dependencies.kafka = { status: 'disabled', mandatory: kafkaMandatory };
  }

  const providers = configuredProviders();
  dependencies.runtime_providers = {
    status: providers.some(provider => provider.status === 'fallback' || provider.status === 'simulated')
      ? 'unhealthy'
      : 'healthy',
    mandatory: activeRuntimeMode() === 'production',
  };

  const requiredHealthy = Object.values(dependencies).every(
    dependency => !dependency.mandatory || dependency.status === 'healthy'
  );

  return {
    status: requiredHealthy ? 'ready' : 'not_ready',
    request_id: requestId,
    timestamp: new Date().toISOString(),
    dependencies,
  };
}
