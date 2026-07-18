import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { judiciaryCaseService } from '../services/judiciary-case.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Civilization judiciary routes (build phase C8). */
export async function judiciaryCaseRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/judiciary/cases', { config: requirePrincipal('judiciary.case.open') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const b = (req.body ?? {}) as any;
      if (!b.dispute_type || !b.title || !b.respondent_scope_type || !b.respondent_scope_id) {
        throw new PublicHttpError(400, 'dispute_type, title, respondent_scope_type, respondent_scope_id are required');
      }
      // AUD-004 (cond 16): the complainant is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.openCase({ ...b, complainant_actor_id: req.principal!.actorId });
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

  fastify.post('/api/civilization/judiciary/cases/:caseId/jurisdiction', { config: requirePrincipal('judiciary.jurisdiction.check') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (typeof b.accept !== 'boolean') throw new PublicHttpError(400, 'accept (boolean) is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await judiciaryCaseService.checkJurisdiction({ case_id: caseId, ...b, actor_id: req.principal!.actorId });
      return { done: true };
    })
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/evidence-collection', { config: requirePrincipal('judiciary.evidence_collection.open') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await judiciaryCaseService.openEvidenceCollection(caseId, req.principal!.actorId);
      return { opened: true };
    })
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/evidence', { config: requirePrincipal('judiciary.evidence.submit') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.statement) throw new PublicHttpError(400, 'statement is required');
      // AUD-004: submitted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.submitEvidence({ case_id: caseId, ...b, submitted_by_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/hearing', { config: requirePrincipal('judiciary.hearing.hold') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.summary) throw new PublicHttpError(400, 'summary is required');
      // AUD-004: presiding_actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.holdHearing({ case_id: caseId, ...b, presiding_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/ruling', { config: requirePrincipal('judiciary.ruling.issue') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.outcome || !b.rationale) throw new PublicHttpError(400, 'outcome, rationale are required');
      // AUD-004 (cond 16): the ruling judge is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.issueRuling({ case_id: caseId, ...b, ruling_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/enforcement', { config: requirePrincipal('judiciary.enforcement.issue') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.order_type || !b.target_scope_type || !b.target_scope_id) {
        throw new PublicHttpError(400, 'order_type, target_scope_type, target_scope_id are required');
      }
      // AUD-004: issued_by_actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.issueEnforcement({ case_id: caseId, ...b, issued_by_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/rulings/:rulingId/dissent', { config: requirePrincipal('judiciary.dissent.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { rulingId } = req.params as { rulingId: string };
      const b = (req.body ?? {}) as any;
      if (!b.opinion) throw new PublicHttpError(400, 'opinion is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.recordDissent({ ruling_id: rulingId, ...b, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/appeal', { config: requirePrincipal('judiciary.appeal.file') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.grounds) throw new PublicHttpError(400, 'grounds is required');
      // AUD-004: appellant_actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.fileAppeal({ case_id: caseId, ...b, appellant_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/appeal/ruling', { config: requirePrincipal('judiciary.appeal.decide') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      const b = (req.body ?? {}) as any;
      if (!b.outcome || !b.rationale) throw new PublicHttpError(400, 'outcome, rationale are required');
      // AUD-004 (cond 16): the appellate authority is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.ruleOnAppeal({ case_id: caseId, ...b, appellate_actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/judiciary/cases/:caseId/finalize', { config: requirePrincipal('judiciary.case.finalize') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { caseId } = req.params as { caseId: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return judiciaryCaseService.finalizeCase({ case_id: caseId, actor_id: req.principal!.actorId });
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
