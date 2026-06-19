import { FastifyInstance } from 'fastify';
import { issueCredential } from '../services/credential.service';

export async function credentialRoutes(fastify: FastifyInstance) {
  fastify.get<{ Params: { agent_id: string } }>('/api/credential/:agent_id', async (req, reply) => {
    const credential = await issueCredential(req.params.agent_id);
    if (!credential) {
      return reply.status(404).send({
        error: 'no resolved non-post-hoc predictions for agent',
        recompute: {
          command: `python3 reserve/tools/recompute_credential.py ${req.params.agent_id}`,
        },
      });
    }
    return reply.send({ credential });
  });
}
