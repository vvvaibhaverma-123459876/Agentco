import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import {
  identityAuthorityService,
  RegisterActorInput,
  AssignRoleInput,
  GrantPermissionInput,
} from '../services/identity-authority.service';

function errorStatus(error: unknown): number {
  const message = error instanceof Error ? error.message : String(error);
  if (
    message.includes('required') ||
    message.includes('invalid') ||
    message.includes('must') ||
    message.includes('unknown') ||
    message.includes('not found') ||
    message.includes('not active')
  ) {
    return 400;
  }
  return 500;
}

async function sendError(reply: FastifyReply, error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return reply.status(errorStatus(error)).send({ error: message });
}

export async function identityRoutes(fastify: FastifyInstance) {
  fastify.post(
    '/identity/actors',
    async (request: FastifyRequest<{ Body: RegisterActorInput }>, reply) => {
      try {
        const actor = await identityAuthorityService.registerActor(request.body);
        return reply.status(201).send({ actor });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/roles/assign',
    async (request: FastifyRequest<{ Body: AssignRoleInput }>, reply) => {
      try {
        const result = await identityAuthorityService.assignRole(request.body);
        return reply.status(201).send(result);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/permissions/grant',
    async (request: FastifyRequest<{ Body: GrantPermissionInput }>, reply) => {
      try {
        const result = await identityAuthorityService.grantPermission(request.body);
        return reply.status(201).send(result);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/verify',
    async (
      request: FastifyRequest<{ Body: { actor_id: string; permission_name: string; scope?: string } }>,
      reply
    ) => {
      try {
        const decision = await identityAuthorityService.verifyAuthority(
          request.body.actor_id,
          request.body.permission_name,
          request.body.scope
        );
        return reply.status(decision.allowed ? 200 : 403).send(decision);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );
}
