import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { societyService, SocietyStatus } from '../services/society.service';
import { institutionGovernance } from '../services/institution-governance.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';

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

  fastify.post('/api/civilization/societies', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as { name?: string; description?: string; created_by_actor_id?: string };
      if (!body.name) return reply.status(400).send({ error: 'name is required' });
      return societyService.createSociety(body as { name: string; description?: string; created_by_actor_id?: string });
    }, 201)
  );

  fastify.get('/api/civilization/societies', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => societyService.listSocieties())
  );

  fastify.post('/api/civilization/societies/bootstrap-defaults', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { actor_id } = (req.body ?? {}) as { actor_id?: string };
      return societyService.ensureDefaultSocieties(actor_id);
    }, 201)
  );

  fastify.get('/api/civilization/societies/topology', async (_req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => societyService.getTopology())
  );

  fastify.post('/api/civilization/societies/:societyId/transition', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { to_status?: SocietyStatus; actor_id?: string; reason?: string };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      return societyService.transitionSociety({
        society_id: societyId, to_status: body.to_status, actor_id: body.actor_id, reason: body.reason,
      });
    })
  );

  fastify.post('/api/civilization/societies/:societyId/jurisdictions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { jurisdiction_key?: string; granted_by_actor_id?: string };
      if (!body.jurisdiction_key) return reply.status(400).send({ error: 'jurisdiction_key is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return societyService.addJurisdiction({
        society_id: societyId,
        jurisdiction_key: body.jurisdiction_key,
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/societies/:societyId/citizens', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { citizen_id?: string; role_in_society?: string; actor_id?: string };
      if (!body.citizen_id) return reply.status(400).send({ error: 'citizen_id is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return societyService.joinSociety({
        society_id: societyId, citizen_id: body.citizen_id,
        role_in_society: body.role_in_society, actor_id: body.actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/societies/:societyId/citizens/:citizenId/leave', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId, citizenId } = req.params as { societyId: string; citizenId: string };
      const body = (req.body ?? {}) as { actor_id?: string; reason?: string };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      await societyService.leaveSociety({
        society_id: societyId, citizen_id: citizenId, actor_id: body.actor_id, reason: body.reason ?? '',
      });
      return { left: true };
    })
  );

  fastify.post('/api/civilization/societies/:societyId/institutions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { societyId } = req.params as { societyId: string };
      const body = (req.body ?? {}) as { institution_id?: string; actor_id?: string };
      if (!body.institution_id) return reply.status(400).send({ error: 'institution_id is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return societyService.attachInstitution({
        society_id: societyId, institution_id: body.institution_id, actor_id: body.actor_id,
      });
    }, 201)
  );

  // ---- Institution governance ----

  fastify.post('/api/civilization/institutions/bootstrap-mandatory', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { actor_id } = (req.body ?? {}) as { actor_id?: string };
      return institutionGovernance.ensureMandatoryInstitutions(actor_id);
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/charter', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as { charter?: Record<string, unknown>; actor_id?: string; activate?: boolean };
      if (!body.charter || typeof body.charter !== 'object') {
        return reply.status(400).send({ error: 'charter object is required' });
      }
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      const draft = await institutionGovernance.proposeCharter({
        institution_id: institutionId, charter: body.charter, actor_id: body.actor_id,
      });
      if (body.activate === true) {
        await institutionGovernance.activateCharter(draft.id, body.actor_id);
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

  fastify.post('/api/civilization/institutions/:institutionId/mandates', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        mandate_key?: string; description?: string; department_name?: string; granted_by_actor_id?: string;
      };
      if (!body.mandate_key) return reply.status(400).send({ error: 'mandate_key is required' });
      if (!body.description) return reply.status(400).send({ error: 'description is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return institutionGovernance.addMandate({
        institution_id: institutionId, mandate_key: body.mandate_key,
        description: body.description, department_name: body.department_name,
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/powers', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        power_key?: string; scope?: Record<string, unknown>;
        authorized_decision_ref?: string; granted_by_actor_id?: string;
      };
      if (!body.power_key) return reply.status(400).send({ error: 'power_key is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return institutionGovernance.grantPower({
        institution_id: institutionId, power_key: body.power_key, scope: body.scope,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/limits', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as {
        limit_key?: string; limit_value?: Record<string, unknown>; granted_by_actor_id?: string;
      };
      if (!body.limit_key) return reply.status(400).send({ error: 'limit_key is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return institutionGovernance.setLimit({
        institution_id: institutionId, limit_key: body.limit_key,
        limit_value: body.limit_value, granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/institutions/:institutionId/jurisdiction', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { institutionId } = req.params as { institutionId: string };
      const body = (req.body ?? {}) as { jurisdiction_key?: string; granted_by_actor_id?: string };
      if (!body.jurisdiction_key) return reply.status(400).send({ error: 'jurisdiction_key is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return societyService.grantInstitutionCivilizationJurisdiction({
        institution_id: institutionId,
        jurisdiction_key: body.jurisdiction_key,
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  // ---- Inter-institution contracts ----

  fastify.post('/api/civilization/contracts', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        from_institution_id?: string; to_institution_id?: string; title?: string;
        terms?: Record<string, unknown>; commitments?: Array<Record<string, unknown>>;
        proposed_by_actor_id?: string;
      };
      if (!body.from_institution_id) return reply.status(400).send({ error: 'from_institution_id is required' });
      if (!body.to_institution_id) return reply.status(400).send({ error: 'to_institution_id is required' });
      if (!body.title) return reply.status(400).send({ error: 'title is required' });
      if (!body.proposed_by_actor_id) return reply.status(400).send({ error: 'proposed_by_actor_id is required' });
      return institutionGovernance.proposeContract({
        from_institution_id: body.from_institution_id,
        to_institution_id: body.to_institution_id,
        title: body.title,
        terms: body.terms,
        commitments: body.commitments,
        proposed_by_actor_id: body.proposed_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/contracts/:contractId/transition', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { contractId } = req.params as { contractId: string };
      const body = (req.body ?? {}) as {
        to_status?: 'accepted' | 'active' | 'fulfilled' | 'breached' | 'terminated';
        actor_id?: string; reason?: string; settlement?: Record<string, unknown>;
      };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      return institutionGovernance.transitionContract({
        contract_id: contractId, to_status: body.to_status,
        actor_id: body.actor_id, reason: body.reason, settlement: body.settlement,
      });
    })
  );
}
