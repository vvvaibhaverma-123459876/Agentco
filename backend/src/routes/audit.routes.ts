import { FastifyInstance } from 'fastify';
import { auditLog } from '../services/audit-log.service';

export async function auditRoutes(fastify: FastifyInstance) {
  fastify.get('/api/audit', async (req, reply) => {
    const { agent_id, risk_level, human_approved, from, to, limit = '50', offset = '0' } = req.query as Record<string, string>;
    const parsedLimit = parseInt(limit, 10);
    const parsedOffset = parseInt(offset, 10);
    if (isNaN(parsedLimit) || isNaN(parsedOffset) || parsedLimit < 0 || parsedOffset < 0) {
      return reply.status(400).send({ error: 'Invalid limit or offset' });
    }
    const entries = await auditLog.query({
      agent_id, risk_level,
      human_approved: human_approved !== undefined ? human_approved === 'true' : undefined,
      from, to,
      limit: parsedLimit, offset: parsedOffset,
    });
    return reply.send({ entries, count: entries.length });
  });

  fastify.get('/api/audit/integrity', async (_req, reply) => {
    const result = await auditLog.verifyChainIntegrity();
    return reply.send(result);
  });
}
