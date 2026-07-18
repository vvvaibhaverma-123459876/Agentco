import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { safeEvolution } from '../services/safe-evolution.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Learning / safe-evolution routes (build phase C10). */
export async function safeEvolutionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/learning/candidates', { config: requirePrincipal('evolution.candidate.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.source || !b.learning_form || !b.title || !b.hypothesis) {
        throw new PublicHttpError(400, 'source, learning_form, title, hypothesis are required');
      }
      // AUD-004: proposer_actor_id is the AUTHENTICATED principal, never a body field.
      return safeEvolution.createCandidate({ ...b, proposer_actor_id: req.principal!.actorId });
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

  fastify.post('/api/civilization/learning/candidates/:candidateId/failure-analysis', { config: requirePrincipal('evolution.candidate.record_failure_analysis') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.failure_summary || !b.root_cause) throw new PublicHttpError(400, 'failure_summary, root_cause are required');
      // AUD-004: analysed_by_actor_id is the AUTHENTICATED principal, never a body field.
      await safeEvolution.recordFailureAnalysis({ candidate_id: candidateId, ...b, analysed_by_actor_id: req.principal!.actorId });
      return { analysed: true };
    }, 201)
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/regressions', { config: requirePrincipal('evolution.candidate.generate_regressions') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return safeEvolution.generateRegressions({ candidate_id: candidateId, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/sandbox', { config: requirePrincipal('evolution.candidate.mark_sandboxed') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await safeEvolution.markSandboxed({ candidate_id: candidateId, actor_id: req.principal!.actorId });
      return { sandboxed: true };
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/evaluate', { config: requirePrincipal('evolution.evaluate') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (typeof b.cases_passed !== 'number') throw new PublicHttpError(400, 'cases_passed is required');
      // AUD-004 (cond 25): the evaluator is the AUTHENTICATED principal, never a body field.
      return safeEvolution.evaluate({
        candidate_id: candidateId, evaluator_actor_id: req.principal!.actorId, cases_passed: b.cases_passed,
        safety_non_regression: b.safety_non_regression ?? false,
        calibration_non_regression: b.calibration_non_regression ?? false,
        evidence_non_regression: b.evidence_non_regression ?? false, detail: b.detail,
      });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/canary', { config: requirePrincipal('evolution.canary.start') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return safeEvolution.startCanary({ candidate_id: candidateId, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/learning/canaries/:canaryId/report', { config: requirePrincipal('evolution.canary.report') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { canaryId } = req.params as { canaryId: string };
      const b = (req.body ?? {}) as any;
      if (typeof b.clean !== 'boolean') throw new PublicHttpError(400, 'clean (boolean) is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return safeEvolution.reportCanary({ canary_id: canaryId, ...b, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/promote', { config: requirePrincipal('evolution.approve') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.artifact_hash) throw new PublicHttpError(400, 'artifact_hash is required');
      // AUD-004 (cond 25): the approver is the AUTHENTICATED principal, never a body field.
      return safeEvolution.promote({ candidate_id: candidateId, ...b, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/rollback', { config: requirePrincipal('evolution.candidate.rollback') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      const b = (req.body ?? {}) as any;
      if (!b.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return safeEvolution.rollback({ candidate_id: candidateId, ...b, actor_id: req.principal!.actorId });
    })
  );

  fastify.post('/api/civilization/learning/candidates/:candidateId/retain', { config: requirePrincipal('evolution.candidate.retain') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { candidateId } = req.params as { candidateId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await safeEvolution.retain({ candidate_id: candidateId, actor_id: req.principal!.actorId });
      return { retained: true };
    })
  );
}
