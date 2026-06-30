import dotenv from 'dotenv';
dotenv.config();

import Fastify from 'fastify';
import cors from '@fastify/cors';
import websocket from '@fastify/websocket';
import { agentRoutes } from './routes/agents.routes';
import { overrideRoutes } from './routes/override.routes';
import { auditRoutes } from './routes/audit.routes';
import { credentialRoutes } from './routes/credential.routes';
import { learningRoutes } from './services/learning.service';
import { registerLearningMiddleware } from './middleware/learning.middleware';
import { civilizationRequestValidator } from './middleware/civilization-request-validator';
import { assertProductionSecrets } from './security';
import { assertNoProductionFallbackProviders, activeRuntimeMode, configuredProviders } from './runtime-mode';
import { autonomyTaskRoutes } from './routes/autonomy-tasks.routes';
import { autonomyOrchestratorRoutes } from './routes/autonomy-orchestrator.routes';
import { autonomyDashboardRoutes } from './routes/autonomy-dashboard.routes';
import { civilizationGovernanceRoutes } from './routes/civilization-governance.routes';
import { institutionWorkAssignmentRoutes } from './routes/institution-work-assignment.routes';
import { goalHierarchyRoutes } from './routes/goal-hierarchy.routes';
import { phase3HardeningRoutes } from './routes/phase3-hardening.routes';
import { systemRoutes } from './routes/system.routes';
import { identityRoutes } from './routes/identity.routes';
import { resourceLedgerRoutes } from './routes/resource-ledger.routes';
import { metricsService } from './services/autonomy-metrics.service';
import { shutdownRuntimeResources } from './runtime/shutdown';

const PORT = parseInt(process.env.PORT ?? '3001');
const HOST = process.env.HOST ?? '0.0.0.0';

export async function build() {
  assertProductionSecrets();
  assertNoProductionFallbackProviders();
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: process.env.FRONTEND_URL ?? 'http://localhost:3000' });
  await app.register(websocket);

  // Register learning middleware (captures all signals across the system)
  await registerLearningMiddleware(app);

  // Register civilization request validator (body size, rate limiting)
  await civilizationRequestValidator(app);

  // Rate limiting map: track requests per API key
  const rateLimitMap = new Map<string, { count: number; resetAt: number }>();
  const RATE_LIMIT_WINDOW = 60000; // 1 minute
  const RATE_LIMIT_MAX_REQUESTS = 100;

  app.addHook('preHandler', async (request, reply) => {
    const method = request.method.toUpperCase();
    const apiKey = process.env.AGENTCO_API_KEY;

    if (!apiKey || ['GET', 'HEAD', 'OPTIONS'].includes(method)) return;

    const provided = request.headers['x-api-key'];
    if (provided !== apiKey) {
      return reply.status(401).send({ error: 'write API key required' });
    }

    // Rate limiting
    const now = Date.now();
    const identifier = provided || 'anonymous';
    const rateLimit = rateLimitMap.get(identifier);

    if (rateLimit && rateLimit.resetAt > now) {
      if (rateLimit.count >= RATE_LIMIT_MAX_REQUESTS) {
        return reply.status(429).send({
          error: 'Rate limit exceeded',
          retryAfter: Math.ceil((rateLimit.resetAt - now) / 1000)
        });
      }
      rateLimit.count++;
    } else {
      rateLimitMap.set(identifier, { count: 1, resetAt: now + RATE_LIMIT_WINDOW });
    }
  });

  // Centralized error handler
  app.setErrorHandler(async (error: any, request, reply) => {
    const requestId = request.id || 'unknown';
    const statusCode = error?.statusCode || 500;
    const message = error?.message || 'Internal server error';

    console.error(`[${requestId}] Error in ${request.method} ${request.url}:`, error);

    const response = {
      error: message,
      status_code: statusCode,
      request_id: requestId,
      timestamp: new Date().toISOString(),
    };

    reply.status(statusCode).send(response);
  });

  await app.register(agentRoutes);
  await app.register(overrideRoutes);
  await app.register(auditRoutes);
  await app.register(credentialRoutes);
  await app.register(learningRoutes);
  await app.register(autonomyTaskRoutes);
  await app.register(autonomyOrchestratorRoutes);
  await app.register(autonomyDashboardRoutes);
  await app.register(civilizationGovernanceRoutes);
  await app.register(institutionWorkAssignmentRoutes);
  await app.register(goalHierarchyRoutes);
  await app.register(phase3HardeningRoutes);
  await app.register(identityRoutes);
  await app.register(resourceLedgerRoutes);
  await app.register(systemRoutes);

  // Basic health check
  app.get('/health', async () => ({
    status: 'ok',
    timestamp: new Date().toISOString(),
  }));

  app.get('/health/runtime', async () => ({
    status: 'ok',
    runtime_mode: activeRuntimeMode(),
    providers: configuredProviders(),
    fallback_active: configuredProviders().some(provider => provider.status === 'fallback' || provider.status === 'simulated'),
    timestamp: new Date().toISOString(),
  }));

  // Detailed health check with component status
  app.get('/health/detailed', async (request, reply) => {
    const checks: Record<string, boolean> = {};

    try {
      await import('./db/client').then(async ({ db }) => {
        const result = await db.query('SELECT 1');
        checks.database = !!result.rows.length;
      });
    } catch (err) {
      checks.database = false;
      console.warn('Health check: database check failed:', err);
    }

    // Kafka check (optional - producer may not be connected yet)
    try {
      await import('./db/kafka').then(async ({ kafka }) => {
        checks.kafka = true;
      });
    } catch (err) {
      checks.kafka = false;
    }

    const allHealthy = Object.values(checks).every(v => v);
    const statusCode = allHealthy ? 200 : 503;

    reply.status(statusCode).send({
      status: allHealthy ? 'healthy' : 'degraded',
      checks,
      timestamp: new Date().toISOString(),
    });
  });

  // Prometheus metrics endpoint
  app.get('/metrics', async (request, reply) => {
    try {
      const metrics = metricsService.getMetrics();
      const contentType = metricsService.getContentType();
      reply.type(contentType);
      return metrics;
    } catch (error: any) {
      console.error('Error generating metrics:', error);
      reply.status(500).send({ error: 'Failed to generate metrics' });
    }
  });

  // WebSocket for real-time event stream
  app.get('/ws/events', { websocket: true }, (socket) => {
    socket.send(JSON.stringify({ type: 'connected', message: 'Agentco event stream' }));
  });

  return app;
}

async function main() {
  const app = await build();
  try {
    await app.listen({ port: PORT, host: HOST });
    console.log(`Agentco API running on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }

  const gracefulShutdown = async (signal: string) => {
    console.log(`Received ${signal}, shutting down gracefully...`);
    try {
      await app.close();
      await shutdownRuntimeResources({ closeDb: true });
      console.log('Server closed gracefully');
      process.exit(0);
    } catch (err) {
      console.error('Error during shutdown:', err);
      process.exit(1);
    }
  };

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));
}

if (require.main === module) {
  main();
}
