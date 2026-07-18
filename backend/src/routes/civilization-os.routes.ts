import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { civilizationOs, OsMode } from '../services/civilization-os.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Civilization operating system routes (build phase C12). */
export async function civilizationOsRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  // Manual/debug trigger of a tick over HTTP. The production path is the scheduler worker
  // calling civilizationOs.tick() directly in-process (civilization-scheduler-worker.ts),
  // not this route; gate this administrative trigger with a real principal.
  fastify.post('/api/civilization/os/tick', { config: requirePrincipal('civilization_os.tick.trigger') }, async (_req: FastifyRequest, reply: FastifyReply) =>
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

  fastify.post('/api/civilization/os/start', { config: requirePrincipal('civilization_os.daemon.start') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationOs.startDaemon(b.interval_ms ?? 60000, req.principal!.actorId);
    })
  );

  // AUD-004: this route can halt the entire civilization tick loop -- kill-switch-adjacent.
  fastify.post('/api/civilization/os/stop', { config: requirePrincipal('civilization_os.daemon.stop') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationOs.stopDaemon(req.principal!.actorId);
    })
  );

  fastify.post('/api/civilization/os/mode', { config: requirePrincipal('civilization_os.mode.set') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      const mode = b.mode as OsMode;
      if (!['running', 'paused', 'drained', 'stopped'].includes(mode)) throw new PublicHttpError(400, 'mode must be running, paused, drained, or stopped');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await civilizationOs.setMode(mode, req.principal!.actorId);
      return { mode };
    })
  );
}
