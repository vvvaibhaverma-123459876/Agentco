import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { judiciaryCaseService } from '../services/judiciary-case.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Civilization judiciary routes (build phase C8). */
export async function judiciaryCaseRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/judiciary/cases', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.dispute_type || !b.title || !b.complainant_actor_id || !b.respondent_scope_type || !b.respondent_scope_id) {
        throw new PublicHttpError(400, 'dispute_type, title, complainant_actor_id, respondent_scope_type, respondent_scope_id are required');
      }
      return judiciaryCaseService.openCase(b);
    }, 201)
  );

  fastify.get('/api/civilization/judiciary/cases/:caseId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const c = await judiciaryCaseService.getCase(caseId);
      if (!c) throw new PublicHttpError(404, 'not found');
      return c;
    })
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/jurisdiction', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || typeof b.accept !== 'boolean') throw new PublicHttpError(400, 'actor_id and accept (boolean) are required');
      await judiciaryCaseService.checkJurisdiction({ case_id: caseId, ...b });
      return { done: true };
    })
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/evidence-collection', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await judiciaryCaseService.openEvidenceCollection(caseId, b.actor_id);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/evidence', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.submitted_by_actor_id || !b.statement) throw new PublicHttpError(400, 'submitted_by_actor_id and statement are required');
      return judiciaryCaseService.submitEvidence({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/hearing', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.presiding_actor_id || !b.summary) throw new PublicHttpError(400, 'presiding_actor_id and summary are required');
      return judiciaryCaseService.holdHearing({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/ruling', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.ruling_actor_id || !b.outcome || !b.rationale) throw new PublicHttpError(400, 'ruling_actor_id, outcome, rationale are required');
      return judiciaryCaseService.issueRuling({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/enforcement', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.issued_by_actor_id || !b.order_type || !b.target_scope_type || !b.target_scope_id) {
        throw new PublicHttpError(400, 'issued_by_actor_id, order_type, target_scope_type, target_scope_id are required');
      }
      return judiciaryCaseService.issueEnforcement({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/rulings/:rulingId/dissent', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { rulingId } = req.params as { rulingId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id || !b.opinion) throw new PublicHttpError(400, 'actor_id and opinion are required');
      return judiciaryCaseService.recordDissent({ ruling_id: rulingId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/appeal', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.appellant_actor_id || !b.grounds) throw new PublicHttpError(400, 'appellant_actor_id and grounds are required');
      return judiciaryCaseService.fileAppeal({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/appeal/ruling', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.appellate_actor_id || !b.outcome || !b.rationale) throw new PublicHttpError(400, 'appellate_actor_id, outcome, rationale are required');
      return judiciaryCaseService.ruleOnAppeal({ case_id: caseId, ...b });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/finalize', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return judiciaryCaseService.finalizeCase({ case_id: caseId, actor_id: b.actor_id });
    })
  );

  fastify.get('/api/civilization/judiciary/precedents/:disputeType', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { disputeType } = req.params as { disputeType: string };
      const { outcome } = req.query as { outcome?: string };
      return judiciaryCaseService.findPrecedents({ dispute_type: disputeType, outcome });
    })
  );
}
