import Fastify from 'fastify';
import cors from '@fastify/cors';
import websocket from '@fastify/websocket';
import { agentRoutes } from './routes/agents.routes';
import { overrideRoutes } from './routes/override.routes';
import { auditRoutes } from './routes/audit.routes';

const PORT = parseInt(process.env.PORT ?? '3001');
const HOST = process.env.HOST ?? '0.0.0.0';

async function build() {
  const app = Fastify({ logger: true });

  await app.register(cors, { origin: process.env.FRONTEND_URL ?? 'http://localhost:3000' });
  await app.register(websocket);

  await app.register(agentRoutes);
  await app.register(overrideRoutes);
  await app.register(auditRoutes);

  app.get('/health', async () => ({ status: 'ok', timestamp: new Date().toISOString() }));

  // WebSocket for real-time event stream
  app.get('/ws/events', { websocket: true }, (socket) => {
    socket.send(JSON.stringify({ type: 'connected', message: 'AgentCo event stream' }));
  });

  return app;
}

async function main() {
  const app = await build();
  try {
    await app.listen({ port: PORT, host: HOST });
    console.log(`AgentCo API running on ${HOST}:${PORT}`);
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

main();
