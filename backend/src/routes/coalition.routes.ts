import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { coalitionService } from '../services/coalition.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Institution coalition routes (build phase C4). */
export async function coalitionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/coalitions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.name) throw new PublicHttpError(400, 'name is required');
      if (!Array.isArray(body.member_institution_ids)) throw new PublicHttpError(400, 'member_institution_ids array is required');
      if (!body.created_by_actor_id) throw new PublicHttpError(400, 'created_by_actor_id is required');
      return coalitionService.proposeCoalition(body);
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

  fastify.post('/api/civilization/coalitions/:coalitionId/negotiate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return coalitionService.openNegotiation({ coalition_id: coalitionId, actor_id: body.actor_id });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/proposals', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || !body.actor_id || typeof body.round_number !== 'number' || !body.proposal) {
        throw new PublicHttpError(400, 'round_number, institution_id, actor_id, proposal are required');
      }
      return coalitionService.submitProposal({ coalition_id: coalitionId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/dissents', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || !body.actor_id || !body.reason) {
        throw new PublicHttpError(400, 'institution_id, actor_id, reason are required');
      }
      return coalitionService.recordDissent({ coalition_id: coalitionId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/consensus', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (typeof body.round_number !== 'number' || !body.actor_id || !Array.isArray(body.acceptances)) {
        throw new PublicHttpError(400, 'round_number, actor_id, acceptances[] are required');
      }
      return coalitionService.resolveConsensus({ coalition_id: coalitionId, ...body });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/commitments', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.institution_id || !body.actor_id || !body.commitment) {
        throw new PublicHttpError(400, 'institution_id, actor_id, commitment are required');
      }
      return coalitionService.commit({ coalition_id: coalitionId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/constitute', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return coalitionService.constitute({ coalition_id: coalitionId, actor_id: body.actor_id });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/activate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return coalitionService.activate({ coalition_id: coalitionId, actor_id: body.actor_id });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/delegations', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.from_institution_id || !body.delegated_authority_key || !body.granted_by_actor_id) {
        throw new PublicHttpError(400, 'from_institution_id, delegated_authority_key, granted_by_actor_id are required');
      }
      return coalitionService.grantDelegation({ coalition_id: coalitionId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/settle', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id || !body.settlement) {
        throw new PublicHttpError(400, 'actor_id and settlement are required');
      }
      return coalitionService.settle({ coalition_id: coalitionId, actor_id: body.actor_id, settlement: body.settlement });
    })
  );

  fastify.post('/api/civilization/coalitions/:coalitionId/terminate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { coalitionId } = req.params as { coalitionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id || !body.terminal_status || !body.reason) {
        throw new PublicHttpError(400, 'actor_id, terminal_status, reason are required');
      }
      return coalitionService.terminate({ coalition_id: coalitionId, ...body });
    })
  );
}
