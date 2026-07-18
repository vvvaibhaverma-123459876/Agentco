import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { treasuryService, ScopeType, EconomyResource } from '../services/treasury.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Civilization economy / treasury routes (build phase C6). */
export async function treasuryRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/treasury/accounts', { config: requirePrincipal('treasury.account.open') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type) {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.openAccount({ ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.get('/api/civilization/treasury/accounts/:scopeType/:scopeId/:resourceType', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { scopeType, scopeId, resourceType } = req.params as { scopeType: ScopeType; scopeId: string; resourceType: EconomyResource };
      const balance = await treasuryService.balance(scopeType, scopeId, resourceType);
      if (!balance) throw new PublicHttpError(404, 'not found');
      return balance;
    })
  );

  fastify.post('/api/civilization/treasury/fund', { config: requirePrincipal('treasury.account.fund') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type || typeof b.amount !== 'number') {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type, amount are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.fund({ reason: b.reason ?? 'funding', ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/policies', { config: requirePrincipal('treasury.policy.set') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.policy_key || !b.resource_type) {
        throw new PublicHttpError(400, 'policy_key, resource_type are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.setPolicy({ ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/evaluate', { config: requirePrincipal('treasury.request.evaluate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type || typeof b.amount !== 'number') {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type, amount are required');
      }
      return treasuryService.evaluateRequest(b);
    })
  );

  fastify.post('/api/civilization/treasury/budgets', { config: requirePrincipal('treasury.budget.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.from_scope || !b.to_scope || !b.resource_type || typeof b.amount !== 'number') {
        throw new PublicHttpError(400, 'from_scope, to_scope, resource_type, amount are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.proposeBudget({ ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/budgets/:proposalId/decide', { config: requirePrincipal('treasury.budget.decide') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (typeof b.approve !== 'boolean') throw new PublicHttpError(400, 'approve (boolean) is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.decideBudget({ proposal_id: proposalId, approve: b.approve, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/treasury/budgets/:proposalId/allocate', { config: requirePrincipal('treasury.budget.allocate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.allocateBudget({ proposal_id: proposalId, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/treasury/penalties', { config: requirePrincipal('treasury.penalty.impose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.target_scope || !b.resource_type || typeof b.amount !== 'number' || !b.authority) {
        throw new PublicHttpError(400, 'target_scope, resource_type, amount, authority are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field. (Residual: the
      // 'authority' claim itself ('governance'|'judiciary') is still caller-asserted and not
      // yet verified against the principal's actual role -- tracked as a follow-up, not fixed here.)
      return treasuryService.imposePenalty({ authorized_decision_ref: b.authorized_decision_ref ?? '', reason: b.reason ?? '', ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/costs', { config: requirePrincipal('treasury.cost.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.resource_type || typeof b.amount !== 'number') {
        throw new PublicHttpError(400, 'resource_type, amount are required');
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.recordCost({ ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.get('/api/civilization/treasury/costs/rollup/:dimension', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { dimension } = req.params as { dimension: 'mission' | 'institution' | 'domain' };
      const { resource_type } = req.query as { resource_type?: EconomyResource };
      if (!['mission', 'institution', 'domain'].includes(dimension)) throw new PublicHttpError(400, 'invalid dimension');
      return treasuryService.costRollup(dimension, resource_type);
    })
  );

  fastify.post('/api/civilization/treasury/reconcile', { config: requirePrincipal('treasury.reconcile') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.resource_type) throw new PublicHttpError(400, 'resource_type is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return treasuryService.reconcile({ ...b, actor_id: req.principal!.actorId });
    })
  );
}
