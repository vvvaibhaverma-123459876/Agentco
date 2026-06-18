import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function reserveRoutes(fastify: FastifyInstance) {
  fastify.get('/api/reserve/credentials', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT DISTINCT ON (subject_id, domain, horizon_class)
           subject_id AS agent_id, domain, horizon_class, trust_factor, n_resolved, computed_at
         FROM trust_scores
         ORDER BY subject_id, domain, horizon_class, computed_at DESC`
      );
      return reply.send({ credentials: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'reserve credentials query failed');
      return reply.send({ credentials: [], count: 0 });
    }
  });

  fastify.get<{ Params: { agent_id: string } }>(
    '/api/reserve/credentials/:agent_id', async (req, reply) => {
      try {
        const rows = await query(
          `SELECT DISTINCT ON (domain, horizon_class)
             subject_id AS agent_id, domain, horizon_class, trust_factor, n_resolved, computed_at
           FROM trust_scores WHERE subject_id = $1
           ORDER BY domain, horizon_class, computed_at DESC`,
          [req.params.agent_id]
        );
        return reply.send({ agent_id: req.params.agent_id, credentials: rows });
      } catch (err) {
        fastify.log.error(err, 'reserve credentials agent query failed');
        return reply.send({ agent_id: req.params.agent_id, credentials: [] });
      }
    }
  );

  fastify.post<{ Params: { agent_id: string } }>(
    '/api/reserve/verify/:agent_id', async (req, reply) => {
      const { agent_id } = req.params;
      try {
        const stored = await query<{ trust_factor: number }>(
          `SELECT trust_factor FROM trust_scores WHERE subject_id = $1 ORDER BY computed_at DESC LIMIT 1`,
          [agent_id]
        ).catch(() => [] as Array<{ trust_factor: number }>);

        const stored_trust_factor: number | null = stored[0]?.trust_factor ?? null;

        const ledger = await query<{ n: string; brier_mean: string | null }>(
          `SELECT COUNT(*) AS n,
             AVG(POWER(probability - CASE WHEN resolved_outcome = true THEN 1.0 ELSE 0.0 END, 2)) AS brier_mean
           FROM prediction_ledger
           WHERE producing_agent_id = $1 AND resolved = true AND probability IS NOT NULL`,
          [agent_id]
        ).catch(() => [] as Array<{ n: string; brier_mean: string | null }>);

        const n = parseInt(ledger[0]?.n ?? '0', 10);
        const brier = parseFloat(ledger[0]?.brier_mean ?? '0.25');
        const recomputed_trust_factor = n > 0 ? Math.max(0, Math.round((1 - brier) * 10000) / 10000) : null;
        const match = stored_trust_factor !== null && recomputed_trust_factor !== null
          && Math.abs(stored_trust_factor - recomputed_trust_factor) < 0.01;

        return reply.send({ agent_id, stored_trust_factor, recomputed_trust_factor, match, n_predictions_checked: n });
      } catch (err) {
        fastify.log.error(err, 'reserve verify failed');
        return reply.status(500).send({ error: 'Verification failed', agent_id });
      }
    }
  );

  fastify.get('/api/reserve/oracle-standing', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT subject_id, domain, horizon_class, trust_factor, n_resolved, computed_at
         FROM trust_scores WHERE subject_type = 'oracle' ORDER BY computed_at DESC`
      );
      return reply.send({ oracle_standing: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'oracle-standing query failed');
      return reply.send({ oracle_standing: [], count: 0 });
    }
  });
}
