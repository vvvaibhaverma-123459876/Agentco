import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import {
  identityAuthorityService,
  RegisterActorInput,
  AssignRoleInput,
  GrantPermissionInput,
  GrantDelegationInput,
  RegisterKeyInput,
  VerifySignatureInput,
} from '../services/identity-authority.service';
import { requirePrincipal } from '../auth/principal-context';

function errorStatus(error: unknown): number {
  const message = error instanceof Error ? error.message : String(error);
  if (
    message.includes('required') ||
    message.includes('invalid') ||
    message.includes('must') ||
    message.includes('not accepted') ||
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
  // AUD-004 bootstrap note: intentionally NOT gated with requirePrincipal. Registering a new,
  // unprivileged actor row is the entry point INTO the identity substrate -- requiring an
  // existing signed principal here would create a bootstrap deadlock (no actor can ever
  // register the first actor). Registration alone grants no authority; the consequential
  // actions (role/permission/delegation/key grants below) DO require an authenticated
  // principal. This route remains behind the global API-key preHandler. Residual: consider
  // a dedicated bootstrap/admin credential path if unattended actor self-registration is
  // ever exposed beyond a trusted operator.
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
    { config: requirePrincipal('identity.role.assign') },
    async (request: FastifyRequest<{ Body: AssignRoleInput }>, reply) => {
      try {
        // AUD-004: assigned_by is the AUTHENTICATED principal, never a body field.
        // actor_id (the role recipient) is the SUBJECT and stays from the body.
        const result = await identityAuthorityService.assignRole({ ...request.body, assigned_by: request.principal!.actorId });
        return reply.status(201).send(result);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/permissions/grant',
    { config: requirePrincipal('identity.permission.grant') },
    async (request: FastifyRequest<{ Body: GrantPermissionInput }>, reply) => {
      try {
        // AUD-004: granted_by is the AUTHENTICATED principal, never a body field.
        // actor_id (the permission recipient) is the SUBJECT and stays from the body.
        const result = await identityAuthorityService.grantPermission({ ...request.body, granted_by: request.principal!.actorId });
        return reply.status(201).send(result);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/delegations/grant',
    { config: requirePrincipal('identity.delegation.grant') },
    async (request: FastifyRequest<{ Body: GrantDelegationInput }>, reply) => {
      try {
        // AUD-004: granted_by is the AUTHENTICATED principal, never a body field.
        // principal_actor_id/delegate_actor_id (the delegation parties) are SUBJECTS and stay from the body.
        const result = await identityAuthorityService.grantDelegation({ ...request.body, granted_by: request.principal!.actorId });
        return reply.status(201).send(result);
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/keys',
    { config: requirePrincipal('identity.key.register') },
    async (request: FastifyRequest<{ Body: RegisterKeyInput }>, reply) => {
      try {
        // AUD-004: created_by is the AUTHENTICATED principal, never a body field.
        // actor_id (the key owner) is the SUBJECT and stays from the body.
        const key = await identityAuthorityService.registerKey({ ...request.body, created_by: request.principal!.actorId });
        return reply.status(201).send({ key });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/keys/:keyId/revoke',
    { config: requirePrincipal('identity.key.revoke') },
    async (request: FastifyRequest<{ Params: { keyId: string } }>, reply) => {
      try {
        // AUD-004: revoked_by is the AUTHENTICATED principal, never a body field.
        const key = await identityAuthorityService.revokeKey(request.params.keyId, request.principal!.actorId);
        return reply.status(200).send({ key });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/identity/keys/verify-signature',
    async (request: FastifyRequest<{ Body: VerifySignatureInput }>, reply) => {
      try {
        const result = await identityAuthorityService.verifySignature(request.body);
        return reply.status(result.valid ? 200 : 403).send(result);
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
