import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { collectiveKnowledge, KnowledgeType } from '../services/collective-knowledge.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Collective epistemics routes (build phase C9). */
export async function collectiveKnowledgeRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/knowledge/provenance', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.from_type || !b.from_id || !b.to_type || !b.to_id || !b.actor_id) {
        throw new PublicHttpError(400, 'from_type, from_id, to_type, to_id, actor_id are required');
      }
      return collectiveKnowledge.linkProvenance(b);
    }, 201)
  );

  fastify.post('/api/civilization/knowledge/retract', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.subject_type || !b.subject_id || !b.reason || !b.actor_id) {
        throw new PublicHttpError(400, 'subject_type, subject_id, reason, actor_id are required');
      }
      return collectiveKnowledge.retract(b);
    }, 201)
  );

  fastify.get('/api/civilization/knowledge/retractions/:retractionId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { retractionId } = req.params as { retractionId: string };
      const r = await collectiveKnowledge.getRetraction(retractionId);
      if (!r) throw new PublicHttpError(404, 'not found');
      return r;
    })
  );

  fastify.get('/api/civilization/knowledge/status/:type/:id', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { type, id } = req.params as { type: KnowledgeType; id: string };
      return { type, id, retracted: await collectiveKnowledge.isRetracted(type, id) };
    })
  );

  fastify.get('/api/civilization/knowledge', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { domain, limit } = req.query as { domain?: string; limit?: string };
      return collectiveKnowledge.civilizationKnowledge({ domain, limit: limit ? parseInt(limit) : undefined });
    })
  );
}
