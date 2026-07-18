import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { civilizationKernel, CivilizationStatus } from '../services/civilization-kernel.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

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
  fastify.post('/api/civilization/kernel/bootstrap', { config: requirePrincipal('civilization.kernel.bootstrap') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.ensureCivilizationRoot({ actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/kernel', { config: requirePrincipal('civilization.kernel.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        name?: string; description?: string; charter?: Record<string, unknown>;
      };
      if (!body.name) return reply.status(400).send({ error: 'name is required' });
      // AUD-004: created_by_actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.createCivilization({
        name: body.name,
        description: body.description,
        charter: body.charter,
        created_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/:civilizationId/activate', { config: requirePrincipal('civilization.kernel.activate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.activateCivilization(civilizationId, req.principal!.actorId);
    })
  );

  fastify.post('/api/civilization/kernel/:civilizationId/transition', { config: requirePrincipal('civilization.kernel.transition') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as {
        to_status?: CivilizationStatus; reason?: string; authorized_decision_ref?: string;
      };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.transitionStatus({
        civilization_id: civilizationId,
        to_status: body.to_status,
        actor_id: req.principal!.actorId,
        reason: body.reason,
        authorized_decision_ref: body.authorized_decision_ref,
      });
    })
  );

  fastify.post('/api/civilization/kernel/:civilizationId/emergency', { config: requirePrincipal('civilization.kernel.emergency.declare') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as {
        scope?: string; reason?: string; authorized_decision_ref?: string; ttl_seconds?: number;
      };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.enterEmergency({
        civilization_id: civilizationId,
        scope: body.scope ?? '',
        reason: body.reason ?? '',
        actor_id: req.principal!.actorId,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
        ttl_seconds: Number(body.ttl_seconds),
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/emergency/:emergencyId/revoke', { config: requirePrincipal('civilization.kernel.emergency.revoke') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { emergencyId } = req.params as { emergencyId: string };
      const body = (req.body ?? {}) as { reason?: string };
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.revokeEmergency({
        emergency_id: emergencyId,
        actor_id: req.principal!.actorId,
        reason: body.reason,
      });
    })
  );

  fastify.post('/api/civilization/kernel/emergency/expire-sweep', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => civilizationKernel.expireDueEmergencies())
  );

  fastify.post('/api/civilization/kernel/:civilizationId/charter', { config: requirePrincipal('civilization.kernel.charter.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as { charter?: Record<string, unknown>; activate?: boolean };
      if (!body.charter || typeof body.charter !== 'object') {
        return reply.status(400).send({ error: 'charter object is required' });
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      const draft = await civilizationKernel.proposeCharter({
        civilization_id: civilizationId,
        charter: body.charter,
        actor_id: req.principal!.actorId,
      });
      if (body.activate === true) {
        await civilizationKernel.activateCharter(draft.id, req.principal!.actorId);
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

  fastify.post('/api/civilization/kernel/:civilizationId/objectives', { config: requirePrincipal('civilization.kernel.objective.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { civilizationId } = req.params as { civilizationId: string };
      const body = (req.body ?? {}) as { title?: string; description?: string; priority?: number };
      if (!body.title) return reply.status(400).send({ error: 'title is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.createObjective({
        civilization_id: civilizationId,
        title: body.title,
        description: body.description,
        priority: body.priority,
        actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/kernel/objectives/:objectiveId/status', { config: requirePrincipal('civilization.kernel.objective.status') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { objectiveId } = req.params as { objectiveId: string };
      const body = (req.body ?? {}) as { to_status?: string; reason?: string };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return civilizationKernel.setObjectiveStatus({
        objective_id: objectiveId,
        to_status: body.to_status,
        actor_id: req.principal!.actorId,
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
