import Fastify from 'fastify';
import cors from '@fastify/cors';
import websocket from '@fastify/websocket';
import { agentRoutes } from './routes/agents.routes';
import { overrideRoutes } from './routes/override.routes';
import { auditRoutes } from './routes/audit.routes';
import { credentialRoutes } from './routes/credential.routes';
import { assertProductionSecrets } from './security';

const PORT = parseInt(process.env.PORT ?? '3001');
const HOST = process.env.HOST ?? '0.0.0.0';

export async function build() {
  assertProductionSecrets();
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: process.env.FRONTEND_URL ?? 'http://localhost:3000' });
  await app.register(websocket);

  app.addHook('preHandler', async (request, reply) => {
    const method = request.method.toUpperCase();
    const apiKey = process.env.AGENTCO_API_KEY;
    if (!apiKey || ['GET', 'HEAD', 'OPTIONS'].includes(method)) return;

    const provided = request.headers['x-api-key'];
    if (provided !== apiKey) {
      return reply.status(401).send({ error: 'write API key required' });
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

  // Basic health check
  app.get('/health', async () => ({
    status: 'ok',
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

  // Metrics endpoint for Prometheus
  app.get('/metrics', async () => {
    return metricsService.render();
  });

  // Record request metrics
  app.addHook('onResponse', async (request, reply) => {
    const start = (request as any)._startTime || Date.now();
    const duration = (Date.now() - start) / 1000;
    metricsService.recordHttpRequest(
      request.method,
      request.url.split('?')[0],
      reply.statusCode,
      duration,
    );
  });

  // Record errors
  app.addHook('onError', async (request, reply, error) => {
    metricsService.recordError(error?.name || 'unknown');
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
      await disconnectProducer();
      await app.close();
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
