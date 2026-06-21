import { FastifyInstance } from 'fastify';
import { overrideQueue } from '../services/override-queue.service';
import { requireScope } from '../security';

export async function overrideRoutes(fastify: FastifyInstance) {
  // List all pending override requests
  fastify.get('/api/overrides', async (req, reply) => {
    const { agent_id, risk_level } = req.query as Record<string, string>;
    const items = await overrideQueue.listPending({ agent_id, risk_level });
    return reply.send({ items, count: items.length });
  });

  // Get overdue SLA items
  fastify.get('/api/overrides/overdue', async (_req, reply) => {
    const items = await overrideQueue.getOverdueSla();
    return reply.send({ items, count: items.length });
  });

  // Approve or reject an override request
  fastify.post<{
    Params: { request_id: string };
    Body: { resolution: 'approved' | 'rejected'; resolved_by: string; notes?: string };
  }>('/api/overrides/:request_id/resolve', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const { request_id } = req.params;
    const { resolution, resolved_by, notes } = req.body;

    if (!['approved', 'rejected'].includes(resolution)) {
      return reply.status(400).send({ error: 'resolution must be approved or rejected' });
    }

    const result = await overrideQueue.resolve(request_id, resolution, resolved_by, notes);
    return reply.send(result);
  });

  // Enqueue a new override request (called by agents, not humans)
  fastify.post<{
    Body: { agent_id: string; action: string; risk_level: 'high' | 'critical'; context: Record<string, unknown> };
  }>('/api/overrides', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const { agent_id, action, risk_level, context } = req.body;
    const request = await overrideQueue.enqueue(agent_id, action, risk_level, context);
    return reply.status(201).send(request);
  });
}
