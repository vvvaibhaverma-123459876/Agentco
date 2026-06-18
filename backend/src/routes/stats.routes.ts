import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function statsRoutes(fastify: FastifyInstance) {
  fastify.get('/api/stats', async (_req, reply) => {
    try {
      const fallback: Array<{ count: string }> = [{ count: '0' }];
      const [total, resolved_true, resolved_false, pending, active, events] =
        await Promise.all([
          query<{ count: string }>('SELECT COUNT(*) AS count FROM prediction_ledger').catch(() => fallback),
          query<{ count: string }>('SELECT COUNT(*) AS count FROM prediction_ledger WHERE resolved_outcome = true').catch(() => fallback),
          query<{ count: string }>('SELECT COUNT(*) AS count FROM prediction_ledger WHERE resolved_outcome = false').catch(() => fallback),
          query<{ count: string }>('SELECT COUNT(*) AS count FROM prediction_ledger WHERE resolved = false').catch(() => fallback),
          query<{ count: string }>("SELECT COUNT(*) AS count FROM agent_state WHERE status != 'idle'").catch(() => fallback),
          query<{ count: string }>("SELECT COUNT(*) AS count FROM event_history WHERE timestamp >= NOW() - INTERVAL '1 hour'").catch(() => fallback),
        ]);

      return reply.send({
        predictions_total:          parseInt(total[0]?.count ?? '0', 10),
        predictions_resolved_true:  parseInt(resolved_true[0]?.count ?? '0', 10),
        predictions_resolved_false: parseInt(resolved_false[0]?.count ?? '0', 10),
        predictions_pending:        parseInt(pending[0]?.count ?? '0', 10),
        agents_active:              parseInt(active[0]?.count ?? '0', 10),
        events_last_hour:           parseInt(events[0]?.count ?? '0', 10),
      });
    } catch (err) {
      fastify.log.error(err, 'stats query failed');
      return reply.status(500).send({ error: 'Failed to fetch stats' });
    }
  });
}
