import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function eventsRoutes(fastify: FastifyInstance) {
  fastify.get('/api/events/recent', async (req, reply) => {
    const { limit = '20', event_type } = req.query as Record<string, string | undefined>;
    const parsedLimit = Math.min(parseInt(limit, 10) || 20, 200);
    const params: unknown[] = [];
    const conditions: string[] = [];
    if (event_type) { params.push(event_type); conditions.push(`event_type = $${params.length}`); }
    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    params.push(parsedLimit);
    try {
      const rows = await query(
        `SELECT event_id, event_type, producer_agent_id, timestamp, confidence_score, payload, risk_level
         FROM event_history ${where} ORDER BY timestamp DESC LIMIT $${params.length}`,
        params
      );
      return reply.send({ events: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'events recent query failed');
      return reply.send({ events: [], count: 0 });
    }
  });
}
