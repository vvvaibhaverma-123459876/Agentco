import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function predictionsRoutes(fastify: FastifyInstance) {
  fastify.get('/api/predictions', async (req, reply) => {
    const {
      agent_id, domain, outcome, from, to,
      limit = '50', offset = '0', search,
    } = req.query as Record<string, string | undefined>;

    const params: unknown[] = [];
    const conditions: string[] = [];

    if (agent_id) { params.push(agent_id); conditions.push(`producing_agent_id = $${params.length}`); }
    if (domain)   { params.push(domain);   conditions.push(`domain = $${params.length}`); }
    if (outcome === 'true')    conditions.push('resolved_outcome = true');
    else if (outcome === 'false')   conditions.push('resolved_outcome = false');
    else if (outcome === 'pending') conditions.push('resolved = false');
    if (from) { params.push(from); conditions.push(`created_at >= $${params.length}`); }
    if (to)   { params.push(to);   conditions.push(`created_at <= $${params.length}`); }
    if (search) { params.push(`%${search}%`); conditions.push(`claim ILIKE $${params.length}`); }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    const parsedLimit  = Math.min(parseInt(limit,  10) || 50,  200);
    const parsedOffset = parseInt(offset, 10) || 0;

    try {
      const filterParams = [...params];
      params.push(parsedLimit, parsedOffset);

      const rows = await query(
        `SELECT prediction_id, claim, producing_agent_id, domain, claim_type, probability,
                resolved, resolved_outcome, resolved_at, brier_score, log_score,
                resolution_criterion, resolution_date, ground_truth_source, created_at, was_surprise
         FROM prediction_ledger ${where}
         ORDER BY created_at DESC
         LIMIT $${params.length - 1} OFFSET $${params.length}`,
        params
      );
      const countRows = await query<{ total: string }>(
        `SELECT COUNT(*) AS total FROM prediction_ledger ${where}`, filterParams
      );

      return reply.send({
        predictions: rows,
        total: parseInt(countRows[0]?.total ?? '0', 10),
        limit: parsedLimit,
        offset: parsedOffset,
      });
    } catch (err) {
      fastify.log.error(err, 'predictions query failed');
      return reply.status(500).send({ error: 'Failed to fetch predictions', predictions: [] });
    }
  });

  fastify.get<{ Params: { id: string } }>('/api/predictions/:id', async (req, reply) => {
    try {
      const rows = await query(
        'SELECT * FROM prediction_ledger WHERE prediction_id = $1', [req.params.id]
      );
      if (!rows.length) return reply.status(404).send({ error: 'Prediction not found' });
      return reply.send(rows[0]);
    } catch (err) {
      fastify.log.error(err, 'prediction detail query failed');
      return reply.status(500).send({ error: 'Failed to fetch prediction' });
    }
  });
}
