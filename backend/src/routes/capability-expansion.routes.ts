import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { capabilityExpansion } from '../services/capability-expansion.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Capability / domain expansion routes (build phase C11). */
export async function capabilityExpansionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/expansion/proposals', { config: requirePrincipal('expansion.proposal.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.expansion_type || !b.domain_key || !b.title) {
        throw new PublicHttpError(400, 'expansion_type, domain_key, title are required');
      }
      // AUD-004: the proposer is the AUTHENTICATED principal, never a body field.
      return capabilityExpansion.propose({ ...b, proposer_actor_id: req.principal!.actorId });
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

  fastify.post('/api/civilization/expansion/proposals/:proposalId/stage', { config: requirePrincipal('expansion.proposal.stage') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.stage || typeof b.passed !== 'boolean' || !b.summary) {
        throw new PublicHttpError(400, 'stage, passed (boolean), summary are required');
      }
      // AUD-004: the recording actor is the AUTHENTICATED principal, never a body field.
      await capabilityExpansion.recordStage({ proposal_id: proposalId, ...b, actor_id: req.principal!.actorId });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/expansion/proposals/:proposalId/approve', { config: requirePrincipal('expansion.proposal.approve') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      // AUD-004: the approver is the AUTHENTICATED principal, never a body field.
      return capabilityExpansion.approve({ proposal_id: proposalId, approver_actor_id: req.principal!.actorId, restricted: b.restricted });
    })
  );

  fastify.post('/api/civilization/expansion/proposals/:proposalId/grant', { config: requirePrincipal('expansion.capability.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.capability_key || !b.domain_key || !b.grantee_scope_type || !b.grantee_scope_id) {
        throw new PublicHttpError(400, 'capability_key, domain_key, grantee_scope_type, grantee_scope_id are required');
      }
      // AUD-004: the granting actor is the AUTHENTICATED principal, never a body field.
      return capabilityExpansion.grantCapability({ proposal_id: proposalId, ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/expansion/grants/:grantId/restrict', { config: requirePrincipal('expansion.capability.restrict') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { grantId } = req.params as { grantId: string };
      const b = (req.body ?? {}) as any;
      if (!b.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: the restricting actor is the AUTHENTICATED principal, never a body field.
      await capabilityExpansion.restrictCapability({ grant_id: grantId, restriction: b.restriction ?? {}, ...b, actor_id: req.principal!.actorId });
      return { restricted: true };
    })
  );

  fastify.post('/api/civilization/expansion/grants/:grantId/revoke', { config: requirePrincipal('expansion.capability.revoke') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { grantId } = req.params as { grantId: string };
      const b = (req.body ?? {}) as any;
      if (!b.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: the revoking actor is the AUTHENTICATED principal, never a body field.
      await capabilityExpansion.revokeCapability({ grant_id: grantId, ...b, actor_id: req.principal!.actorId });
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
