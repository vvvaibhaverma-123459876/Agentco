import Fastify from 'fastify';
import cors from '@fastify/cors';
import websocket from '@fastify/websocket';
import { agentRoutes } from './routes/agents.routes';
import { overrideRoutes } from './routes/override.routes';
import { auditRoutes } from './routes/audit.routes';
import { governanceRoutes } from './routes/governance.routes';
import { disconnectProducer } from './db/kafka';

const PORT = parseInt(process.env.PORT ?? '3001');
const HOST = process.env.HOST ?? '0.0.0.0';

async function build() {
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

  await app.register(agentRoutes);
  await app.register(overrideRoutes);
  await app.register(auditRoutes);
  await app.register(governanceRoutes);

  app.get('/health', async () => ({ status: 'ok', timestamp: new Date().toISOString() }));

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

main();
