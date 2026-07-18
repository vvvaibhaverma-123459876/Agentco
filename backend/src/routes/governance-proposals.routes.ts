import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { governanceService } from '../services/governance.service';
import { policyEnforcement } from '../services/policy-enforcement.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Governance proposal / voting / policy routes (build phase C7). */
export async function governanceProposalRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/governance/proposals', { config: requirePrincipal('governance.proposal.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.title || !b.proposal_type) throw new PublicHttpError(400, 'title, proposal_type are required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return governanceService.createProposal({ ...b, actor_id: req.principal!.actorId });
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

  fastify.post('/api/civilization/governance/proposals/:proposalId/sponsor', { config: requirePrincipal('governance.proposal.sponsor') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: sponsor_actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.sponsor({ proposal_id: proposalId, sponsor_actor_id: req.principal!.actorId });
      return { sponsored: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/impact', { config: requirePrincipal('governance.proposal.impact_assess') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.risk_level || !b.summary) throw new PublicHttpError(400, 'risk_level, summary are required');
      // AUD-004: assessor_actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.recordImpactAssessment({ proposal_id: proposalId, ...b, assessor_actor_id: req.principal!.actorId });
      return { assessed: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/deliberation/open', { config: requirePrincipal('governance.deliberation.open') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.openDeliberation(proposalId, req.principal!.actorId);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/deliberation', { config: requirePrincipal('governance.deliberation.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.position || !b.argument) throw new PublicHttpError(400, 'position, argument are required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.recordDeliberation({ proposal_id: proposalId, ...b, actor_id: req.principal!.actorId });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/voting/open', { config: requirePrincipal('governance.voting.open') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.openVoting(proposalId, req.principal!.actorId);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/votes', { config: requirePrincipal('governance.vote') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.vote) throw new PublicHttpError(400, 'vote is required');
      // AUD-004: voter_actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.castVote({ proposal_id: proposalId, ...b, voter_actor_id: req.principal!.actorId });
      return { cast: true };
    }, 201)
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/voting/close', { config: requirePrincipal('governance.voting.close') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return governanceService.closeVoting({ proposal_id: proposalId, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/governance/proposals/:proposalId/activate', { config: requirePrincipal('governance.proposal.activate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return governanceService.activateProposal({ proposal_id: proposalId, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/governance/policies/:policyId/rollback', { config: requirePrincipal('governance.policy.rollback') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { policyId } = req.params as { policyId: string };
      const b = (req.body ?? {}) as any;
      if (!b.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await governanceService.rollbackPolicy({ runtime_policy_id: policyId, actor_id: req.principal!.actorId, reason: b.reason });
      return { rolled_back: true };
    })
  );

  fastify.post('/api/civilization/governance/policies/evaluate', { config: requirePrincipal('governance.policy.evaluate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.action_type) throw new PublicHttpError(400, 'action_type is required');
      return policyEnforcement.evaluate({ action_type: b.action_type, domain: b.domain ?? null, risk_level: b.risk_level });
    })
  );

  fastify.post('/api/civilization/governance/emergency-powers', { config: requirePrincipal('governance.emergency_power.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope || !b.power || typeof b.ttl_seconds !== 'number') {
        throw new PublicHttpError(400, 'scope, power, ttl_seconds are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return governanceService.grantEmergencyPower({
        reason: b.reason ?? '', authorized_decision_ref: b.authorized_decision_ref ?? '', ...b, actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/governance/emergency-powers/expire-sweep', { config: requirePrincipal('governance.emergency_power.expire_sweep') }, async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => governanceService.expireEmergencyPowers())
  );
}
