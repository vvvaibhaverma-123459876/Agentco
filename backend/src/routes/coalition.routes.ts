import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { coalitionService } from '../services/coalition.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Institution coalition routes (build phase C4). */
export async function coalitionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/coalitions', { config: requirePrincipal('coalition.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.name) throw new PublicHttpError(400, 'name is required');
      if (!Array.isArray(body.member_institution_ids)) throw new PublicHttpError(400, 'member_institution_ids array is required');
      // AUD-004: created_by_actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.proposeCoalition({ ...body, created_by_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.get('/api/civilization/coalitions/:coalitionId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const coalition = await coalitionService.getCoalition(coalitionId);
      if (!coalition) throw new PublicHttpError(404, 'not found');
      return coalition;
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/negotiate', { config: requirePrincipal('coalition.negotiate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.openNegotiation({ coalition_id: coalitionId, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/proposals', { config: requirePrincipal('coalition.proposal.submit') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || typeof body.round_number !== 'number' || !body.proposal) {
        throw new PublicHttpError(400, 'round_number, institution_id, proposal are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.submitProposal({ coalition_id: coalitionId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/dissents', { config: requirePrincipal('coalition.dissent.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || !body.reason) {
        throw new PublicHttpError(400, 'institution_id, reason are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.recordDissent({ coalition_id: coalitionId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/consensus', { config: requirePrincipal('coalition.consensus.resolve') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (typeof body.round_number !== 'number' || !Array.isArray(body.acceptances)) {
        throw new PublicHttpError(400, 'round_number, acceptances[] are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.resolveConsensus({ coalition_id: coalitionId, ...body, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/commitments', { config: requirePrincipal('coalition.commitment.commit') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || !body.commitment) {
        throw new PublicHttpError(400, 'institution_id, commitment are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.commit({ coalition_id: coalitionId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/constitute', { config: requirePrincipal('coalition.constitute') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.constitute({ coalition_id: coalitionId, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/activate', { config: requirePrincipal('coalition.activate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.activate({ coalition_id: coalitionId, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/delegations', { config: requirePrincipal('coalition.delegation.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.from_institution_id || !body.delegated_authority_key) {
        throw new PublicHttpError(400, 'from_institution_id, delegated_authority_key are required');
      }
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.grantDelegation({ coalition_id: coalitionId, ...body, granted_by_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/settle', { config: requirePrincipal('coalition.settle') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.settlement) {
        throw new PublicHttpError(400, 'settlement is required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.settle({ coalition_id: coalitionId, actor_id: req.principal!.actorId, settlement: body.settlement });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/terminate', { config: requirePrincipal('coalition.terminate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.terminal_status || !body.reason) {
        throw new PublicHttpError(400, 'terminal_status, reason are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return coalitionService.terminate({ coalition_id: coalitionId, ...body, actor_id: req.principal!.actorId });
    })
  );
}
