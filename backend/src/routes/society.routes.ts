import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { societyService, SocietyStatus } from '../services/society.service';
import { institutionGovernance } from '../services/institution-governance.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Societies + institution governance routes (build phase C3). */
export async function societyRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      const result = await fn();
      return reply.status(successCode).send(result);
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  // ---- Societies ----

  fastify.post('/api/civilization/societies', { config: requirePrincipal('society.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as { name?: string; description?: string };
      if (!body.name) return reply.status(400).send({ error: 'name is required' });
      // AUD-004: created_by_actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.createSociety({ ...body, created_by_actor_id: req.principal!.actorId } as { name: string; description?: string; created_by_actor_id?: string });
    }, 201)
  );

  fastify.get('/api/civilization/societies', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => societyService.listSocieties())
  );

  fastify.post('/api/civilization/societies/bootstrap-defaults', { config: requirePrincipal('society.bootstrap_defaults') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.ensureDefaultSocieties(req.principal!.actorId);
    }, 201)
  );

  fastify.get('/api/civilization/societies/topology', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => societyService.getTopology())
  );

  fastify.post('/api/civilization/societies/:societyId/transition', { config: requirePrincipal('society.transition') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { to_status?: SocietyStatus; reason?: string };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.transitionSociety({
        society_id: societyId, to_status: body.to_status, actor_id: req.principal!.actorId, reason: body.reason,
      });
    })
  );

  fastify.post('/api/civilization/societies/:societyId/jurisdictions', { config: requirePrincipal('society.jurisdiction.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { jurisdiction_key?: string };
      if (!body.jurisdiction_key) return reply.status(400).send({ error: 'jurisdiction_key is required' });
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.addJurisdiction({
        society_id: societyId,
        jurisdiction_key: body.jurisdiction_key,
        granted_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/societies/:societyId/citizens', { config: requirePrincipal('society.citizen.join') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { citizen_id?: string; role_in_society?: string };
      if (!body.citizen_id) return reply.status(400).send({ error: 'citizen_id is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.joinSociety({
        society_id: societyId, citizen_id: body.citizen_id,
        role_in_society: body.role_in_society, actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/societies/:societyId/citizens/:citizenId/leave', { config: requirePrincipal('society.citizen.leave') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId, citizenId } = req.params as { societyId: string; citizenId: string };
      const body = (req.body ?? {}) as { reason?: string };
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await societyService.leaveSociety({
        society_id: societyId, citizen_id: citizenId, actor_id: req.principal!.actorId, reason: body.reason ?? '',
      });
      return { left: true };
    })
  );

  fastify.post('/api/civilization/societies/:societyId/institutions', { config: requirePrincipal('society.institution.attach') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { institution_id?: string };
      if (!body.institution_id) return reply.status(400).send({ error: 'institution_id is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.attachInstitution({
        society_id: societyId, institution_id: body.institution_id, actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  // ---- Institution governance ----

  fastify.post('/api/civilization/institutions/bootstrap-mandatory', { config: requirePrincipal('institution.bootstrap_mandatory') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.ensureMandatoryInstitutions(req.principal!.actorId);
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/charter', { config: requirePrincipal('institution.charter.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as { charter?: Record<string, unknown>; activate?: boolean };
      if (!body.charter || typeof body.charter !== 'object') {
        return reply.status(400).send({ error: 'charter object is required' });
      }
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      const draft = await institutionGovernance.proposeCharter({
        institution_id: institutionId, charter: body.charter, actor_id: req.principal!.actorId,
      });
      if (body.activate === true) {
        await institutionGovernance.activateCharter(draft.id, req.principal!.actorId);
        return { ...draft, status: 'active' };
      }
      return draft;
    }, 201)
  );

  fastify.get('/api/civilization/institutions/:institutionId/governance', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      return institutionGovernance.listGovernance(institutionId);
    })
  );

  fastify.post('/api/civilization/institutions/:institutionId/mandates', { config: requirePrincipal('institution.mandate.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        mandate_key?: string; description?: string; department_name?: string;
      };
      if (!body.mandate_key) return reply.status(400).send({ error: 'mandate_key is required' });
      if (!body.description) return reply.status(400).send({ error: 'description is required' });
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.addMandate({
        institution_id: institutionId, mandate_key: body.mandate_key,
        description: body.description, department_name: body.department_name,
        granted_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/powers', { config: requirePrincipal('institution.power.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        power_key?: string; scope?: Record<string, unknown>;
        authorized_decision_ref?: string;
      };
      if (!body.power_key) return reply.status(400).send({ error: 'power_key is required' });
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.grantPower({
        institution_id: institutionId, power_key: body.power_key, scope: body.scope,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
        granted_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/limits', { config: requirePrincipal('institution.limit.set') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        limit_key?: string; limit_value?: Record<string, unknown>;
      };
      if (!body.limit_key) return reply.status(400).send({ error: 'limit_key is required' });
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.setLimit({
        institution_id: institutionId, limit_key: body.limit_key,
        limit_value: body.limit_value, granted_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/jurisdiction', { config: requirePrincipal('institution.jurisdiction.grant') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as { jurisdiction_key?: string };
      if (!body.jurisdiction_key) return reply.status(400).send({ error: 'jurisdiction_key is required' });
      // AUD-004: granted_by_actor_id is the AUTHENTICATED principal, never a body field.
      return societyService.grantInstitutionCivilizationJurisdiction({
        institution_id: institutionId,
        jurisdiction_key: body.jurisdiction_key,
        granted_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  // ---- Inter-institution contracts ----

  fastify.post('/api/civilization/contracts', { config: requirePrincipal('institution.contract.propose') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        from_institution_id?: string; to_institution_id?: string; title?: string;
        terms?: Record<string, unknown>; commitments?: Array<Record<string, unknown>>;
      };
      if (!body.from_institution_id) return reply.status(400).send({ error: 'from_institution_id is required' });
      if (!body.to_institution_id) return reply.status(400).send({ error: 'to_institution_id is required' });
      if (!body.title) return reply.status(400).send({ error: 'title is required' });
      // AUD-004: proposed_by_actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.proposeContract({
        from_institution_id: body.from_institution_id,
        to_institution_id: body.to_institution_id,
        title: body.title,
        terms: body.terms,
        commitments: body.commitments,
        proposed_by_actor_id: req.principal!.actorId,
      });
    }, 201)
  );

  fastify.post('/api/civilization/contracts/:contractId/transition', { config: requirePrincipal('institution.contract.transition') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { contractId } = req.params as { contractId: string };
      const body = (req.body ?? {}) as {
        to_status?: 'accepted' | 'active' | 'fulfilled' | 'breached' | 'terminated';
        reason?: string; settlement?: Record<string, unknown>;
      };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return institutionGovernance.transitionContract({
        contract_id: contractId, to_status: body.to_status,
        actor_id: req.principal!.actorId, reason: body.reason, settlement: body.settlement,
      });
    })
  );
}
