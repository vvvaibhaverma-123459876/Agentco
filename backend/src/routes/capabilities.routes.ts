import { FastifyInstance } from 'fastify';
import { capabilityRuntime } from '../services/capability-runtime.service';
import { CapabilityRequest } from '../types/capability.types';
import { requirePrincipal } from '../auth/principal-context';

// AUD-004: the wire protocol's `actor.id` and `authorization_context.permissions` are caller-
// supplied fields (part of the agentco-capability-v1 contract) and must never be trusted for an
// authorization decision -- a caller could otherwise claim any actor id and self-grant any
// permission. `requirePrincipal` verifies a signed, credential-bound principal and its REAL
// granted permission at the HTTP boundary; this rebinds both fields to that verified truth before
// the request ever reaches the capability runtime, so the runtime's own authorization_events
// audit trail reflects what was actually verified, not what the caller claimed.
function withVerifiedPrincipal(req: { body: CapabilityRequest; principal?: { actorId: string } }): CapabilityRequest {
  return {
    ...req.body,
    actor: { ...req.body.actor, id: req.principal!.actorId },
    authorization_context: { ...req.body.authorization_context, permissions: ['capability:execute'] },
  };
}

export async function capabilityRoutes(fastify: FastifyInstance) {
  fastify.post<{ Body: CapabilityRequest }>(
    '/v1/capabilities/execute',
    { config: requirePrincipal('capability.execute') },
    async (req, reply) => {
      const response = capabilityRuntime.execute(withVerifiedPrincipal(req));
      return reply.status(response.status === 'completed' ? 200 : response.status === 'denied' ? 403 : 422).send(response);
    }
  );

  fastify.post<{ Body: CapabilityRequest }>(
    '/v1/capabilities/execute-async',
    { config: requirePrincipal('capability.execute') },
    async (req, reply) => {
      const response = capabilityRuntime.execute(withVerifiedPrincipal(req));
      return reply.status(202).send({ attempt_id: response.attempt_id, status: response.status });
    }
  );

  fastify.get<{ Params: { attemptId: string } }>('/v1/capabilities/attempts/:attemptId', async (req, reply) => {
    const attempt = capabilityRuntime.get(req.params.attemptId);
    if (!attempt) return reply.status(404).send({ error: 'not found' });
    return reply.send(attempt);
  });

  fastify.post<{ Params: { attemptId: string } }>(
    '/v1/capabilities/attempts/:attemptId/cancel',
    { config: requirePrincipal('capability.cancel') },
    async (req, reply) => {
      return reply.send(capabilityRuntime.cancel(req.params.attemptId));
    }
  );
}
