import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function trustRoutes(fastify: FastifyInstance) {
  fastify.get('/api/trust-scores', async (req, reply) => {
    const { agent_id, domain, horizon_class } = req.query as Record<string, string | undefined>;
    const params: unknown[] = [];
    const conditions: string[] = [];
    if (agent_id)     { params.push(agent_id);     conditions.push(`subject_id = $${params.length}`); }
    if (domain)       { params.push(domain);       conditions.push(`domain = $${params.length}`); }
    if (horizon_class){ params.push(horizon_class);conditions.push(`horizon_class = $${params.length}`); }
    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    try {
      const rows = await query(
        `SELECT DISTINCT ON (subject_id, domain, horizon_class)
           subject_id AS agent_id, domain, horizon_class, brier_mean, log_mean,
           trust_factor, n_resolved, n_predictions, computed_at
         FROM trust_scores ${where}
         ORDER BY subject_id, domain, horizon_class, computed_at DESC`,
        params
      );
      return reply.send({ trust_scores: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'trust-scores query failed');
      return reply.send({ trust_scores: [], count: 0 });
    }
  });

  fastify.get<{ Params: { agent_id: string } }>(
    '/api/trust-scores/calibration-curve/:agent_id',
    async (req, reply) => {
      const { agent_id } = req.params;
      try {
        const rows = await query(
          `SELECT
             ROUND(probability::numeric, 1) AS stated_confidence,
             AVG(CASE WHEN resolved_outcome = true THEN 1.0 ELSE 0.0 END) AS actual_accuracy,
             COUNT(*) AS n
           FROM prediction_ledger
           WHERE producing_agent_id = $1 AND resolved = true AND probability IS NOT NULL
           GROUP BY ROUND(probability::numeric, 1)
           ORDER BY stated_confidence`,
          [agent_id]
        );
        return reply.send({ agent_id, calibration_curve: rows });
      } catch (err) {
        fastify.log.error(err, 'calibration-curve query failed');
        return reply.send({ agent_id, calibration_curve: [] });
      }
    }
  );
}
