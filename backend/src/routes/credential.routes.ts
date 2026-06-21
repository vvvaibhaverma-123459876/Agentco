import { FastifyInstance } from 'fastify';
import { getCanonicalCredential, issueCanonicalCredential, verifyCanonicalCredential } from '../services/credential.service';
import { requireScope, requireEmergencyShutdownOff } from '../security';

export async function credentialRoutes(fastify: FastifyInstance) {
  fastify.get<{ Params: { agent_id: string } }>('/api/credential/:agent_id', async (req, reply) => {
    const response = await getCanonicalCredential(req.params.agent_id);
    if (!response) {
      return reply.status(404).send({
        error: 'no canonical Proof-of-Calibration credential stored for agent',
        verification: {
          correctness: 'issue or recompute through the canonical Python Reserve path',
          authorship: 'canonical credentials use Ed25519 signatures when issuer key is configured',
          command: `python3 reserve/tools/recompute_credential.py ${req.params.agent_id}`,
        },
      });
    }
    return reply.send(response);
  });

  fastify.post<{ Params: { agent_id: string } }>(
    '/api/credential/:agent_id/issue',
    { preHandler: [requireScope('credential:issue'), requireEmergencyShutdownOff('high')] },
    async (req, reply) => {
      try {
        const issued = await issueCanonicalCredential(req.params.agent_id);
        return reply.status(201).send(issued);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        const statusCode = /no resolved non-post-hoc predictions/i.test(message) ? 404 : 502;
        return reply.status(statusCode).send({
          error: 'canonical credential issuance failed',
          detail: message,
          canonical_source: 'scripts/issue_canonical_credential.py',
        });
      }
    },
  );

  fastify.post<{ Params: { agent_id: string } }>(
    '/api/credential/:agent_id/verify',
    { preHandler: requireScope('credential:verify') },
    async (req, reply) => {
      return reply.send(await verifyCanonicalCredential(req.params.agent_id));
    },
  );
}
