import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { treasuryService, ScopeType, EconomyResource } from '../services/treasury.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Civilization economy / treasury routes (build phase C6). */
export async function treasuryRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/treasury/accounts', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type || !b.actor_id) {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type, actor_id are required');
      }
      return treasuryService.openAccount(b);
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

  fastify.post('/api/civilization/treasury/fund', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type || typeof b.amount !== 'number' || !b.actor_id) {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type, amount, actor_id are required');
      }
      return treasuryService.fund({ reason: b.reason ?? 'funding', ...b });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/policies', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.policy_key || !b.resource_type || !b.actor_id) {
        throw new PublicHttpError(400, 'policy_key, resource_type, actor_id are required');
      }
      return treasuryService.setPolicy(b);
    }, 201)
  );

  fastify.post('/api/civilization/treasury/evaluate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.scope_type || !b.scope_id || !b.resource_type || typeof b.amount !== 'number') {
        throw new PublicHttpError(400, 'scope_type, scope_id, resource_type, amount are required');
      }
      return treasuryService.evaluateRequest(b);
    })
  );

  fastify.post('/api/civilization/treasury/budgets', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.from_scope || !b.to_scope || !b.resource_type || typeof b.amount !== 'number' || !b.actor_id) {
        throw new PublicHttpError(400, 'from_scope, to_scope, resource_type, amount, actor_id are required');
      }
      return treasuryService.proposeBudget(b);
    }, 201)
  );

  fastify.post('/api/civilization/treasury/budgets/:proposalId/decide', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (typeof b.approve !== 'boolean' || !b.actor_id) throw new PublicHttpError(400, 'approve (boolean) and actor_id are required');
      return treasuryService.decideBudget({ proposal_id: proposalId, approve: b.approve, actor_id: b.actor_id });
    })
  );

  fastify.post('/api/civilization/treasury/budgets/:proposalId/allocate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { proposalId } = req.params as { proposalId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return treasuryService.allocateBudget({ proposal_id: proposalId, actor_id: b.actor_id });
    })
  );

  fastify.post('/api/civilization/treasury/penalties', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.target_scope || !b.resource_type || typeof b.amount !== 'number' || !b.authority || !b.actor_id) {
        throw new PublicHttpError(400, 'target_scope, resource_type, amount, authority, actor_id are required');
      }
      return treasuryService.imposePenalty({ authorized_decision_ref: b.authorized_decision_ref ?? '', reason: b.reason ?? '', ...b });
    }, 201)
  );

  fastify.post('/api/civilization/treasury/costs', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.resource_type || typeof b.amount !== 'number' || !b.actor_id) {
        throw new PublicHttpError(400, 'resource_type, amount, actor_id are required');
      }
      return treasuryService.recordCost(b);
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

  fastify.post('/api/civilization/treasury/reconcile', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.resource_type || !b.actor_id) throw new PublicHttpError(400, 'resource_type and actor_id are required');
      return treasuryService.reconcile(b);
    })
  );
}
