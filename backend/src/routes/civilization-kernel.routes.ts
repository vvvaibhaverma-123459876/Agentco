import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { civilizationKernel, CivilizationStatus } from '../services/civilization-kernel.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';

/**
 * Civilization kernel routes (build phase C1). All routes are protected by the
 * global API-key preHandler; none is marked public.
 */
export async function civilizationKernelRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      const result = await fn();
      return reply.status(successCode).send(result);
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  // Topology root summary.
  fastify.get('/api/civilization/kernel/root', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const root = await civilizationKernel.getRoot();
      if (!root) return { civilization: null, bootstrapped: false };
      return { ...root, bootstrapped: true };
    })
  );

  // Idempotent bootstrap of the civilization root.
  fastify.post('/api/civilization/kernel/bootstrap', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { actor_id } = (req.body ?? {}) as { actor_id?: string };
      return civilizationKernel.ensureCivilizationRoot({ actor_id });
    }, 201)
  );

  fastify.post('/api/civilization/kernel', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        name?: string; description?: string; charter?: Record<string, unknown>; created_by_actor_id?: string;
      };
      if (!body.name) return reply.status(400).send({ error: 'name is required' });
      return civilizationKernel.createCivilization({
        name: body.name,
        description: body.description,
        charter: body.charter,
        created_by_actor_id: body.created_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/:civilizationId/activate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const { actor_id } = (req.body ?? {}) as { actor_id?: string };
      return civilizationKernel.activateCivilization(civilizationId, actor_id);
    })
  );

  fastify.post('/api/civilization/kernel/:civilizationId/transition', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as {
        to_status?: CivilizationStatus; actor_id?: string; reason?: string; authorized_decision_ref?: string;
      };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      return civilizationKernel.transitionStatus({
        civilization_id: civilizationId,
        to_status: body.to_status,
        actor_id: body.actor_id,
        reason: body.reason,
        authorized_decision_ref: body.authorized_decision_ref,
      });
    })
  );

  fastify.post('/api/civilization/kernel/:civilizationId/emergency', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as {
        scope?: string; reason?: string; actor_id?: string; authorized_decision_ref?: string; ttl_seconds?: number;
      };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return civilizationKernel.enterEmergency({
        civilization_id: civilizationId,
        scope: body.scope ?? '',
        reason: body.reason ?? '',
        actor_id: body.actor_id,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
        ttl_seconds: Number(body.ttl_seconds),
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/emergency/:emergencyId/revoke', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { emergencyId } = req.params as { emergencyId: string };
      const body = (req.body ?? {}) as { actor_id?: string; reason?: string };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      return civilizationKernel.revokeEmergency({
        emergency_id: emergencyId,
        actor_id: body.actor_id,
        reason: body.reason,
      });
    })
  );

  fastify.post('/api/civilization/kernel/emergency/expire-sweep', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => civilizationKernel.expireDueEmergencies())
  );

  fastify.post('/api/civilization/kernel/:civilizationId/charter', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as { charter?: Record<string, unknown>; actor_id?: string; activate?: boolean };
      if (!body.charter || typeof body.charter !== 'object') {
        return reply.status(400).send({ error: 'charter object is required' });
      }
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      const draft = await civilizationKernel.proposeCharter({
        civilization_id: civilizationId,
        charter: body.charter,
        actor_id: body.actor_id,
      });
      if (body.activate === true) {
        await civilizationKernel.activateCharter(draft.id, body.actor_id);
        return { ...draft, status: 'active' };
      }
      return draft;
    }, 201)
  );

  fastify.get('/api/civilization/kernel/:civilizationId/charter/active', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const charter = await civilizationKernel.getActiveCharter(civilizationId);
      if (!charter) return reply.status(404).send({ error: 'not found' });
      return charter;
    })
  );

  fastify.get('/api/civilization/kernel/:civilizationId/invariants', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      return civilizationKernel.listProtectedInvariants(civilizationId);
    })
  );

  fastify.post('/api/civilization/kernel/:civilizationId/objectives', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as { title?: string; description?: string; priority?: number; actor_id?: string };
      if (!body.title) return reply.status(400).send({ error: 'title is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return civilizationKernel.createObjective({
        civilization_id: civilizationId,
        title: body.title,
        description: body.description,
        priority: body.priority,
        actor_id: body.actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/objectives/:objectiveId/status', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { objectiveId } = req.params as { objectiveId: string };
      const body = (req.body ?? {}) as { to_status?: string; actor_id?: string; reason?: string };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return civilizationKernel.setObjectiveStatus({
        objective_id: objectiveId,
        to_status: body.to_status,
        actor_id: body.actor_id,
        reason: body.reason,
      });
    })
  );

  fastify.get('/api/civilization/kernel/:civilizationId/objectives', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const { status } = req.query as { status?: string };
      return civilizationKernel.listObjectives(civilizationId, status);
    })
  );
}
