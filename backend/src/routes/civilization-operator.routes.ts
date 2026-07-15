import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { civilizationOperator } from '../services/civilization-operator.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';

/** Civilization operator-plane routes (build phase C13). */
export async function civilizationOperatorRoutes(fastify: FastifyInstance): Promise<void> {
  fastify.get('/api/civilization/operator/overview', async (_req: FastifyRequest, reply: FastifyReply) => {
    try {
      return reply.status(200).send(await civilizationOperator.overview());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  });
}
