import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { civilizationOs, OsMode } from '../services/civilization-os.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Civilization operating system routes (build phase C12). */
export async function civilizationOsRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/os/tick', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => civilizationOs.tick())
  );

  fastify.get('/api/civilization/os/status', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => civilizationOs.statusProjection())
  );

  fastify.get('/api/civilization/os/ticks', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { limit } = req.query as { limit?: string };
      return civilizationOs.recentTicks(limit ? parseInt(limit) : undefined);
    })
  );

  fastify.get('/api/civilization/os/recover', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => civilizationOs.recoverAndReport())
  );

  fastify.post('/api/civilization/os/start', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      return civilizationOs.startDaemon(b.interval_ms ?? 60000, b.actor_id);
    })
  );

  fastify.post('/api/civilization/os/stop', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      return civilizationOs.stopDaemon(b.actor_id);
    })
  );

  fastify.post('/api/civilization/os/mode', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      const mode = b.mode as OsMode;
      if (!['running', 'paused', 'drained', 'stopped'].includes(mode)) throw new PublicHttpError(400, 'mode must be running, paused, drained, or stopped');
      await civilizationOs.setMode(mode, b.actor_id);
      return { mode };
    })
  );
}
