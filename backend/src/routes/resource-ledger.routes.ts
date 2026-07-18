import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import {
  CreateAccountInput,
  ReservationInput,
  TransactionInput,
  resourceLedger,
} from '../services/resource-ledger.service';
import { requirePrincipal } from '../auth/principal-context';

function statusFor(error: unknown): number {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes('insufficient')) return 409;
  if (
    message.includes('required') ||
    message.includes('invalid') ||
    message.includes('must') ||
    message.includes('not found') ||
    message.includes('not active')
  ) {
    return 400;
  }
  return 500;
}

async function sendError(reply: FastifyReply, error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return reply.status(statusFor(error)).send({ error: message });
}

export async function resourceLedgerRoutes(fastify: FastifyInstance) {
  fastify.post(
    '/resources/accounts',
    { config: requirePrincipal('resource.account.create') },
    async (request: FastifyRequest<{ Body: CreateAccountInput }>, reply) => {
      try {
        // AUD-004: owner_actor_id is the AUTHENTICATED principal, never a body field.
        const account = await resourceLedger.createAccount({ ...request.body, owner_actor_id: request.principal!.actorId } as CreateAccountInput);
        return reply.status(201).send({ account });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.get(
    '/resources/accounts/:accountId',
    async (request: FastifyRequest<{ Params: { accountId: string } }>, reply) => {
      try {
        const account = await resourceLedger.getAccount(request.params.accountId);
        if (!account) return reply.status(404).send({ error: 'resource account not found' });
        return { account };
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/transactions/credit',
    { config: requirePrincipal('resource.transaction.credit') },
    async (request: FastifyRequest<{ Body: TransactionInput }>, reply) => {
      try {
        // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
        const transaction = await resourceLedger.credit({ ...request.body, actor_id: request.principal!.actorId });
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/transactions/debit',
    { config: requirePrincipal('resource.transaction.debit') },
    async (request: FastifyRequest<{ Body: TransactionInput }>, reply) => {
      try {
        // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
        const transaction = await resourceLedger.debit({ ...request.body, actor_id: request.principal!.actorId });
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations',
    { config: requirePrincipal('resource.reservation.create') },
    async (request: FastifyRequest<{ Body: ReservationInput }>, reply) => {
      try {
        // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
        const reservation = await resourceLedger.reserve({ ...request.body, actor_id: request.principal!.actorId });
        return reply.status(201).send({ reservation });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations/:reservationId/settle',
    { config: requirePrincipal('resource.reservation.settle') },
    async (
      request: FastifyRequest<{
        Params: { reservationId: string };
        Body: { idempotency_key: string; actual_amount?: number };
      }>,
      reply
    ) => {
      try {
        // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
        const transaction = await resourceLedger.settleReservationUsage(
          request.params.reservationId,
          request.principal!.actorId,
          request.body.idempotency_key,
          request.body.actual_amount
        );
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations/:reservationId/release',
    { config: requirePrincipal('resource.reservation.release') },
    async (
      request: FastifyRequest<{ Params: { reservationId: string } }>,
      reply
    ) => {
      try {
        // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
        const reservation = await resourceLedger.releaseReservation(request.params.reservationId, request.principal!.actorId);
        return { reservation };
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post('/resources/reservations/expire', async (request: FastifyRequest<{ Body: { limit?: number } }>) => {
    const expired = await resourceLedger.expireReservations(request.body?.limit);
    return { expired };
  });
}
