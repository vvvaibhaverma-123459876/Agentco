import { FastifyInstance } from 'fastify';
import { capabilityRuntime } from '../services/capability-runtime.service';
import { CapabilityRequest } from '../types/capability.types';

export async function capabilityRoutes(fastify: FastifyInstance) {
  fastify.post<{ Body: CapabilityRequest }>('/v1/capabilities/execute', async (req, reply) => {
    const response = capabilityRuntime.execute(req.body);
    return reply.status(response.status === 'completed' ? 200 : response.status === 'denied' ? 403 : 422).send(response);
  });

  fastify.post<{ Body: CapabilityRequest }>('/v1/capabilities/execute-async', async (req, reply) => {
    const response = capabilityRuntime.execute(req.body);
    return reply.status(202).send({ attempt_id: response.attempt_id, status: response.status });
  });

  fastify.get<{ Params: { attemptId: string } }>('/v1/capabilities/attempts/:attemptId', async (req, reply) => {
    const attempt = capabilityRuntime.get(req.params.attemptId);
    if (!attempt) return reply.status(404).send({ error: 'not found' });
    return reply.send(attempt);
  });

  fastify.post<{ Params: { attemptId: string } }>('/v1/capabilities/attempts/:attemptId/cancel', async (req, reply) => {
    return reply.send(capabilityRuntime.cancel(req.params.attemptId));
  });
}
