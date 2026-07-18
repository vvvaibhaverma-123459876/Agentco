import { FastifyInstance } from 'fastify';
import { overrideQueue } from '../services/override-queue.service';
import { requireApiKey } from '../security';
import { requirePrincipal } from '../auth/principal-context';

export async function overrideRoutes(fastify: FastifyInstance) {
  // List all pending override requests
  fastify.get('/api/overrides', { preHandler: requireApiKey }, async (req, reply) => {
    const { agent_id, risk_level } = req.query as Record<string, string>;
    const items = await overrideQueue.listPending({ agent_id, risk_level });
    return reply.send({ items, count: items.length });
  });

  // Get overdue SLA items
  fastify.get('/api/overrides/overdue', { preHandler: requireApiKey }, async (_req, reply) => {
    const items = await overrideQueue.getOverdueSla();
    return reply.send({ items, count: items.length });
  });

  // Approve or reject an override request
  fastify.post<{
    Params: { request_id: string };
    Body: { resolution: 'approved' | 'rejected'; notes?: string };
  }>('/api/overrides/:request_id/resolve', { preHandler: requireApiKey, config: requirePrincipal('override.resolve') }, async (req, reply) => {
    const { request_id } = req.params;
    const { resolution, notes } = req.body;

    if (!['approved', 'rejected'].includes(resolution)) {
      return reply.status(400).send({ error: 'resolution must be approved or rejected' });
    }

    // AUD-004: resolved_by is the AUTHENTICATED principal, never a body field.
    const result = await overrideQueue.resolve(request_id, resolution, req.principal!.actorId, notes);
    return reply.send(result);
  });

  // Enqueue a new override request (called by agents, not humans)
  fastify.post<{
    Body: { action: string; risk_level: 'high' | 'critical'; context: Record<string, unknown> };
  }>('/api/overrides', { preHandler: requireApiKey, config: requirePrincipal('override.enqueue') }, async (req, reply) => {
    const { action, risk_level, context } = req.body;
    // AUD-004: agent_id is the AUTHENTICATED principal, never a body field.
    const request = await overrideQueue.enqueue(req.principal!.actorId, action, risk_level, context);
    return reply.status(201).send(request);
  });
}
