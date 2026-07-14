import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { capabilityExpansion } from '../services/capability-expansion.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Capability / domain expansion routes (build phase C11). */
export async function capabilityExpansionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/expansion/proposals', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.expansion_type || !b.domain_key || !b.title || !b.proposer_actor_id) {
        throw new PublicHttpError(400, 'expansion_type, domain_key, title, proposer_actor_id are required');
      }
      return capabilityExpansion.propose(b);
    }, 201)
  );

  fastify.get('/api/civilization/expansion/proposals/:proposalId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const p = await capabilityExpansion.getProposal(proposalId);
      if (!p) throw new PublicHttpError(404, 'not found');
      return p;
    })
  );

  fastify.post('/api/civilization/expansion/proposals/:proposalId/stage', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.stage || typeof b.passed !== 'boolean' || !b.summary || !b.actor_id) {
        throw new PublicHttpError(400, 'stage, passed (boolean), summary, actor_id are required');
      }
      await capabilityExpansion.recordStage({ proposal_id: proposalId, ...b });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/expansion/proposals/:proposalId/approve', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.approver_actor_id) throw new PublicHttpError(400, 'approver_actor_id is required');
      return capabilityExpansion.approve({ proposal_id: proposalId, approver_actor_id: b.approver_actor_id, restricted: b.restricted });
    })
  );

  fastify.post('/api/civilization/expansion/proposals/:proposalId/grant', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.capability_key || !b.domain_key || !b.grantee_scope_type || !b.grantee_scope_id || !b.actor_id) {
        throw new PublicHttpError(400, 'capability_key, domain_key, grantee_scope_type, grantee_scope_id, actor_id are required');
      }
      return capabilityExpansion.grantCapability({ proposal_id: proposalId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/expansion/grants/:grantId/restrict', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { grantId } = req.params as { grantId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      await capabilityExpansion.restrictCapability({ grant_id: grantId, restriction: b.restriction ?? {}, ...b });
      return { restricted: true };
    })
  );

  fastify.post('/api/civilization/expansion/grants/:grantId/revoke', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { grantId } = req.params as { grantId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      await capabilityExpansion.revokeCapability({ grant_id: grantId, ...b });
      return { revoked: true };
    })
  );

  fastify.get('/api/civilization/expansion/capability-status', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const q = req.query as any;
      if (!q.capability_key || !q.domain_key || !q.grantee_scope_type || !q.grantee_scope_id) {
        throw new PublicHttpError(400, 'capability_key, domain_key, grantee_scope_type, grantee_scope_id are required');
      }
      return capabilityExpansion.isCapabilityActive(q);
    })
  );
}
