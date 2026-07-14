import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { safeEvolution } from '../services/safe-evolution.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Learning / safe-evolution routes (build phase C10). */
export async function safeEvolutionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/learning/candidates', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.source || !b.learning_form || !b.title || !b.hypothesis || !b.proposer_actor_id) {
        throw new PublicHttpError(400, 'source, learning_form, title, hypothesis, proposer_actor_id are required');
      }
      return safeEvolution.createCandidate(b);
    }, 201)
  );

  fastify.get('/api/civilization/learning/candidates/:candidateId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const c = await safeEvolution.getCandidate(candidateId);
      if (!c) throw new PublicHttpError(404, 'not found');
      return c;
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/failure-analysis', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.failure_summary || !b.root_cause || !b.analysed_by_actor_id) throw new PublicHttpError(400, 'failure_summary, root_cause, analysed_by_actor_id are required');
      await safeEvolution.recordFailureAnalysis({ candidate_id: candidateId, ...b });
      return { analysed: true };
    }, 201)
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/regressions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return safeEvolution.generateRegressions({ candidate_id: candidateId, actor_id: b.actor_id });
    }, 201)
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/sandbox', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await safeEvolution.markSandboxed({ candidate_id: candidateId, actor_id: b.actor_id });
      return { sandboxed: true };
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/evaluate', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.evaluator_actor_id || typeof b.cases_passed !== 'number') throw new PublicHttpError(400, 'evaluator_actor_id and cases_passed are required');
      return safeEvolution.evaluate({
        candidate_id: candidateId, evaluator_actor_id: b.evaluator_actor_id, cases_passed: b.cases_passed,
        safety_non_regression: b.safety_non_regression ?? false,
        calibration_non_regression: b.calibration_non_regression ?? false,
        evidence_non_regression: b.evidence_non_regression ?? false, detail: b.detail,
      });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/canary', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return safeEvolution.startCanary({ candidate_id: candidateId, actor_id: b.actor_id });
    }, 201)
  );

  fastify.post('/api/civilization/learning/canaries/:canaryId/report', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { canaryId } = req.params as { canaryId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || typeof b.clean !== 'boolean') throw new PublicHttpError(400, 'actor_id and clean (boolean) are required');
      return safeEvolution.reportCanary({ canary_id: canaryId, ...b });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/promote', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.artifact_hash) throw new PublicHttpError(400, 'actor_id and artifact_hash are required');
      return safeEvolution.promote({ candidate_id: candidateId, ...b });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/rollback', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      return safeEvolution.rollback({ candidate_id: candidateId, ...b });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/retain', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await safeEvolution.retain({ candidate_id: candidateId, actor_id: b.actor_id });
      return { retained: true };
    })
  );
}
