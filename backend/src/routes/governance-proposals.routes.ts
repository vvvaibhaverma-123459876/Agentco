import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { governanceService } from '../services/governance.service';
import { policyEnforcement } from '../services/policy-enforcement.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Governance proposal / voting / policy routes (build phase C7). */
export async function governanceProposalRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/governance/proposals', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.title || !b.proposal_type || !b.actor_id) throw new PublicHttpError(400, 'title, proposal_type, actor_id are required');
      return governanceService.createProposal(b);
    }, 201)
  );

  fastify.get('/api/civilization/governance/proposals/:proposalId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const proposal = await governanceService.getProposal(proposalId);
      if (!proposal) throw new PublicHttpError(404, 'not found');
      return proposal;
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/sponsor', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.sponsor_actor_id) throw new PublicHttpError(400, 'sponsor_actor_id is required');
      await governanceService.sponsor({ proposal_id: proposalId, sponsor_actor_id: b.sponsor_actor_id });
      return { sponsored: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/impact', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.assessor_actor_id || !b.risk_level || !b.summary) throw new PublicHttpError(400, 'assessor_actor_id, risk_level, summary are required');
      await governanceService.recordImpactAssessment({ proposal_id: proposalId, ...b });
      return { assessed: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/deliberation/open', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await governanceService.openDeliberation(proposalId, b.actor_id);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/deliberation', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.position || !b.argument) throw new PublicHttpError(400, 'actor_id, position, argument are required');
      await governanceService.recordDeliberation({ proposal_id: proposalId, ...b });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/voting/open', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await governanceService.openVoting(proposalId, b.actor_id);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/votes', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.voter_actor_id || !b.vote) throw new PublicHttpError(400, 'voter_actor_id and vote are required');
      await governanceService.castVote({ proposal_id: proposalId, ...b });
      return { cast: true };
    }, 201)
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/voting/close', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return governanceService.closeVoting({ proposal_id: proposalId, actor_id: b.actor_id });
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/activate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return governanceService.activateProposal({ proposal_id: proposalId, actor_id: b.actor_id });
    })
  );

  fastify.post('/api/civilization/governance/policies/:policyId/rollback', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { policyId } = req.params as { policyId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      await governanceService.rollbackPolicy({ runtime_policy_id: policyId, actor_id: b.actor_id, reason: b.reason });
      return { rolled_back: true };
    })
  );

  fastify.post('/api/civilization/governance/policies/evaluate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.action_type) throw new PublicHttpError(400, 'action_type is required');
      return policyEnforcement.evaluate({ action_type: b.action_type, domain: b.domain ?? null, risk_level: b.risk_level });
    })
  );

  fastify.post('/api/civilization/governance/emergency-powers', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope || !b.power || !b.actor_id || typeof b.ttl_seconds !== 'number') {
        throw new PublicHttpError(400, 'scope, power, actor_id, ttl_seconds are required');
      }
      return governanceService.grantEmergencyPower({
        reason: b.reason ?? '', authorized_decision_ref: b.authorized_decision_ref ?? '', ...b,
      });
    }, 201)
  );

  fastify.post('/api/civilization/governance/emergency-powers/expire-sweep', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => governanceService.expireEmergencyPowers())
  );
}
