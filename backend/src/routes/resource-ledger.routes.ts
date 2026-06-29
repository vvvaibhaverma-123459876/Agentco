import { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import {
  CreateAccountInput,
  ReservationInput,
  TransactionInput,
  resourceLedger,
} from '../services/resource-ledger.service';

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
    async (request: FastifyRequest<{ Body: CreateAccountInput }>, reply) => {
      try {
        const account = await resourceLedger.createAccount(request.body);
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
    async (request: FastifyRequest<{ Body: TransactionInput }>, reply) => {
      try {
        const transaction = await resourceLedger.credit(request.body);
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/transactions/debit',
    async (request: FastifyRequest<{ Body: TransactionInput }>, reply) => {
      try {
        const transaction = await resourceLedger.debit(request.body);
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations',
    async (request: FastifyRequest<{ Body: ReservationInput }>, reply) => {
      try {
        const reservation = await resourceLedger.reserve(request.body);
        return reply.status(201).send({ reservation });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations/:reservationId/settle',
    async (
      request: FastifyRequest<{
        Params: { reservationId: string };
        Body: { actor_id: string; idempotency_key: string };
      }>,
      reply
    ) => {
      try {
        const transaction = await resourceLedger.settleReservation(
          request.params.reservationId,
          request.body.actor_id,
          request.body.idempotency_key
        );
        return reply.status(201).send({ transaction });
      } catch (error) {
        return sendError(reply, error);
      }
    }
  );

  fastify.post(
    '/resources/reservations/:reservationId/release',
    async (
      request: FastifyRequest<{ Params: { reservationId: string }; Body: { actor_id: string } }>,
      reply
    ) => {
      try {
        const reservation = await resourceLedger.releaseReservation(request.params.reservationId, request.body.actor_id);
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
