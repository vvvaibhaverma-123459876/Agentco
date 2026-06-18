import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function civilizationRoutes(fastify: FastifyInstance) {
  fastify.get('/api/civilization/institutions', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT i.*, COALESCE(json_agg(d.*) FILTER (WHERE d.department_id IS NOT NULL), '[]') AS departments
         FROM institutions i
         LEFT JOIN departments d ON d.institution_id = i.institution_id
         GROUP BY i.institution_id ORDER BY i.name`
      );
      return reply.send({ institutions: rows, count: rows.length });
    } catch (err) {
      fastify.log.warn(err, 'civilization institutions table may not exist');
      return reply.send({ institutions: [], count: 0 });
    }
  });

  fastify.get('/api/civilization/reviews', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT r.*, i.name AS institution_name
         FROM institution_output_reviews r
         LEFT JOIN institutions i ON i.institution_id = r.institution_id
         ORDER BY r.reviewed_at DESC LIMIT 100`
      );
      return reply.send({ reviews: rows, count: rows.length });
    } catch (err) {
      fastify.log.warn(err, 'civilization reviews table may not exist');
      return reply.send({ reviews: [], count: 0 });
    }
  });

  fastify.get('/api/civilization/reputation', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT r.*, i.name AS institution_name
         FROM institution_reputation_scores r
         LEFT JOIN institutions i ON i.institution_id = r.institution_id
         ORDER BY r.computed_at DESC`
      );
      return reply.send({ reputation: rows, count: rows.length });
    } catch (err) {
      fastify.log.warn(err, 'civilization reputation table may not exist');
      return reply.send({ reputation: [], count: 0 });
    }
  });

  fastify.get('/api/civilization/governance', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT * FROM governance_decisions ORDER BY decided_at DESC LIMIT 100`
      );
      return reply.send({ governance: rows, count: rows.length });
    } catch (err) {
      fastify.log.warn(err, 'civilization governance table may not exist');
      return reply.send({ governance: [], count: 0 });
    }
  });
}
