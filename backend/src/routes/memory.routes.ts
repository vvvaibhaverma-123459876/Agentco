import { FastifyInstance } from 'fastify';
import { query } from '../db/client';

export async function memoryRoutes(fastify: FastifyInstance) {
  fastify.get('/api/memory/lessons', async (_req, reply) => {
    try {
      const rows = await query(
        `SELECT memory_id, agent_id, memory_type, content, domain, confidence_score, created_at
         FROM agent_memory WHERE memory_type = 'lesson'
         ORDER BY created_at DESC LIMIT 100`
      );
      return reply.send({ lessons: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'memory lessons query failed');
      return reply.send({ lessons: [], count: 0 });
    }
  });

  fastify.get<{ Params: { agent_id: string } }>('/api/memory/:agent_id', async (req, reply) => {
    const { agent_id } = req.params;
    try {
      const [episodic, semantic] = await Promise.all([
        query(
          `SELECT memory_id, agent_id, memory_type, content, domain, confidence_score, created_at, expires_at
           FROM agent_memory WHERE agent_id = $1 AND memory_type = 'episodic'
           ORDER BY created_at DESC LIMIT 100`,
          [agent_id]
        ).catch(() => []),
        query(
          `SELECT memory_id, agent_id, memory_type, content, domain, confidence_score, created_at, expires_at
           FROM agent_memory WHERE agent_id = $1 AND memory_type = 'semantic'
           ORDER BY created_at DESC LIMIT 100`,
          [agent_id]
        ).catch(() => []),
      ]);
      return reply.send({ agent_id, episodic, semantic });
    } catch (err) {
      fastify.log.error(err, 'memory agent query failed');
      return reply.send({ agent_id, episodic: [], semantic: [] });
    }
  });

  fastify.get<{ Params: { agent_id: string } }>('/api/memory/:agent_id/episodes', async (req, reply) => {
    const { agent_id } = req.params;
    try {
      const rows = await query(
        `SELECT memory_id, agent_id, memory_type, content, domain, confidence_score, created_at, expires_at
         FROM agent_memory WHERE agent_id = $1 AND memory_type = 'episodic'
         ORDER BY created_at DESC LIMIT 100`,
        [agent_id]
      );
      return reply.send({ agent_id, episodes: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'memory episodes query failed');
      return reply.send({ agent_id, episodes: [], count: 0 });
    }
  });

  fastify.get<{ Params: { agent_id: string } }>('/api/memory/:agent_id/semantic', async (req, reply) => {
    const { agent_id } = req.params;
    try {
      const rows = await query(
        `SELECT memory_id, agent_id, memory_type, content, domain, confidence_score, created_at, expires_at
         FROM agent_memory WHERE agent_id = $1 AND memory_type = 'semantic'
         ORDER BY created_at DESC LIMIT 100`,
        [agent_id]
      );
      return reply.send({ agent_id, semantic: rows, count: rows.length });
    } catch (err) {
      fastify.log.error(err, 'memory semantic query failed');
      return reply.send({ agent_id, semantic: [], count: 0 });
    }
  });
}
