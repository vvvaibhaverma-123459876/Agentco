import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { citizenshipService, CitizenStatus, RiskLevel } from '../services/citizenship.service';
import { publicMessageForError, statusCodeForError } from '../http-errors';

/** Citizenry routes (build phase C2). All protected by the global API-key preHandler. */
export async function citizenshipRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      const result = await fn();
      return reply.status(successCode).send(result);
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/citizens', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        actor_id?: string; citizen_type?: 'agent' | 'human' | 'service';
        display_name?: string; civilization_id?: string;
      };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.citizen_type || !['agent', 'human', 'service'].includes(body.citizen_type)) {
        return reply.status(400).send({ error: 'citizen_type must be agent, human, or service' });
      }
      return citizenshipService.registerCitizen({
        actor_id: body.actor_id,
        citizen_type: body.citizen_type,
        display_name: body.display_name,
        civilization_id: body.civilization_id,
      });
    }, 201)
  );

  fastify.get('/api/civilization/citizens', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { status, citizen_type } = req.query as { status?: CitizenStatus; citizen_type?: string };
      return citizenshipService.listCitizens({ status, citizen_type });
    })
  );

  fastify.get('/api/civilization/citizens/:citizenId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const citizen = await citizenshipService.getCitizen(citizenId);
      if (!citizen) return reply.status(404).send({ error: 'not found' });
      return citizen;
    })
  );

  fastify.post('/api/civilization/citizens/:citizenId/transition', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const body = (req.body ?? {}) as {
        to_status?: CitizenStatus; actor_id?: string; reason?: string; sanction_id?: string;
      };
      if (!body.to_status) return reply.status(400).send({ error: 'to_status is required' });
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      return citizenshipService.transitionCitizen({
        citizen_id: citizenId,
        to_status: body.to_status,
        actor_id: body.actor_id,
        reason: body.reason,
        sanction_id: body.sanction_id,
      });
    })
  );

  fastify.post('/api/civilization/citizens/:citizenId/sanctions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const body = (req.body ?? {}) as {
        sanction_type?: 'warning' | 'restriction' | 'suspension' | 'expulsion' | 'budget_penalty';
        reason?: string; imposed_by_actor_id?: string; authorized_decision_ref?: string; effective_until?: string;
      };
      if (!body.sanction_type) return reply.status(400).send({ error: 'sanction_type is required' });
      if (!body.imposed_by_actor_id) return reply.status(400).send({ error: 'imposed_by_actor_id is required' });
      return citizenshipService.imposeSanction({
        citizen_id: citizenId,
        sanction_type: body.sanction_type,
        reason: body.reason ?? '',
        imposed_by_actor_id: body.imposed_by_actor_id,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
        effective_until: body.effective_until,
      });
    }, 201)
  );

  fastify.post('/api/civilization/citizens/sanctions/:sanctionId/lift', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { sanctionId } = req.params as { sanctionId: string };
      const body = (req.body ?? {}) as { actor_id?: string; reason?: string };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      if (!body.reason) return reply.status(400).send({ error: 'reason is required' });
      await citizenshipService.liftSanction({ sanction_id: sanctionId, actor_id: body.actor_id, reason: body.reason });
      return { lifted: true };
    })
  );

  fastify.post('/api/civilization/citizens/:citizenId/suspend', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const body = (req.body ?? {}) as {
        reason?: string; imposed_by_actor_id?: string; authorized_decision_ref?: string;
      };
      if (!body.imposed_by_actor_id) return reply.status(400).send({ error: 'imposed_by_actor_id is required' });
      return citizenshipService.suspendCitizen({
        citizen_id: citizenId,
        reason: body.reason ?? '',
        imposed_by_actor_id: body.imposed_by_actor_id,
        authorized_decision_ref: body.authorized_decision_ref ?? '',
      });
    })
  );

  fastify.post('/api/civilization/citizens/:citizenId/roles', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const body = (req.body ?? {}) as {
        role_name?: string; institution_id?: string; domain?: string; valid_to?: string; granted_by_actor_id?: string;
      };
      if (!body.role_name) return reply.status(400).send({ error: 'role_name is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return citizenshipService.grantRoleEligibility({
        citizen_id: citizenId,
        role_name: body.role_name,
        institution_id: body.institution_id,
        domain: body.domain,
        valid_to: body.valid_to,
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/citizens/roles/:eligibilityId/revoke', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { eligibilityId } = req.params as { eligibilityId: string };
      const body = (req.body ?? {}) as { actor_id?: string; reason?: string };
      if (!body.actor_id) return reply.status(400).send({ error: 'actor_id is required' });
      await citizenshipService.revokeRoleEligibility({
        eligibility_id: eligibilityId,
        actor_id: body.actor_id,
        reason: body.reason ?? '',
      });
      return { revoked: true };
    })
  );

  fastify.post('/api/civilization/citizens/:citizenId/envelope', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { citizenId } = req.params as { citizenId: string };
      const body = (req.body ?? {}) as {
        domain?: string; max_risk_level?: RiskLevel; budget_multiplier?: number; granted_by_actor_id?: string;
      };
      if (!body.domain) return reply.status(400).send({ error: 'domain is required' });
      if (!body.max_risk_level) return reply.status(400).send({ error: 'max_risk_level is required' });
      if (!body.granted_by_actor_id) return reply.status(400).send({ error: 'granted_by_actor_id is required' });
      return citizenshipService.setAutonomyEnvelope({
        citizen_id: citizenId,
        domain: body.domain,
        max_risk_level: body.max_risk_level,
        budget_multiplier: body.budget_multiplier,
        granted_by_actor_id: body.granted_by_actor_id,
      });
    }, 201)
  );

  fastify.post('/api/civilization/citizens/successions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as {
        from_citizen_id?: string; to_citizen_id?: string; reason?: string;
        recorded_by_actor_id?: string; scope?: Record<string, unknown>;
      };
      if (!body.from_citizen_id) return reply.status(400).send({ error: 'from_citizen_id is required' });
      if (!body.to_citizen_id) return reply.status(400).send({ error: 'to_citizen_id is required' });
      if (!body.recorded_by_actor_id) return reply.status(400).send({ error: 'recorded_by_actor_id is required' });
      return citizenshipService.recordSuccession({
        from_citizen_id: body.from_citizen_id,
        to_citizen_id: body.to_citizen_id,
        reason: body.reason ?? '',
        recorded_by_actor_id: body.recorded_by_actor_id,
        scope: body.scope,
      });
    }, 201)
  );
}
