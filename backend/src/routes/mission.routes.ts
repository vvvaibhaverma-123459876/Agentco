import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { missionService, MissionStatus } from '../services/mission.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';
import { requirePrincipal } from '../auth/principal-context';

/** Objective/goal/mission routes (build phase C5). */
export async function missionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/strategic-goals', { config: requirePrincipal('mission.strategic_goal.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.createStrategicGoal({ ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/missions', { config: requirePrincipal('mission.create') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.createMission({ ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.get('/api/civilization/missions/:missionId', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const mission = await missionService.getMission(missionId);
      if (!mission) throw new PublicHttpError(404, 'not found');
      return mission;
    })
  );

  fastify.get('/api/civilization/missions/:missionId/attestation', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const attestation = await missionService.getAttestation(missionId);
      if (!attestation) throw new PublicHttpError(404, 'not found');
      return attestation;
    })
  );

  fastify.get('/api/civilization/missions/:missionId/readiness', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      return missionService.completionReadiness(missionId);
    })
  );

  fastify.post('/api/civilization/missions/:missionId/dependencies', { config: requirePrincipal('mission.dependency.add') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.depends_on_mission_id) throw new PublicHttpError(400, 'depends_on_mission_id is required');
      await missionService.addDependency(missionId, body.depends_on_mission_id);
      return { added: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/transition', { config: requirePrincipal('mission.transition') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.to_status) throw new PublicHttpError(400, 'to_status is required');
      if (!body.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.transitionMission({
        mission_id: missionId, to_status: body.to_status as MissionStatus,
        actor_id: req.principal!.actorId, reason: body.reason, block_reason: body.block_reason,
      });
    })
  );

  fastify.post('/api/civilization/missions/:missionId/workstreams', { config: requirePrincipal('mission.workstream.add') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.addWorkstream({ mission_id: missionId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/workstreams/:workstreamId/tasks', { config: requirePrincipal('mission.task.add') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { workstreamId } = req.params as { workstreamId: string };
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.addTask({ workstream_id: workstreamId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/workstreams/:workstreamId/complete', { config: requirePrincipal('mission.workstream.complete') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { workstreamId } = req.params as { workstreamId: string };
      const body = (req.body ?? {}) as any;
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await missionService.completeWorkstream({ workstream_id: workstreamId, actor_id: req.principal!.actorId, status: body.status });
      return { completed: true };
    })
  );

  fastify.post('/api/civilization/mission-tasks/:taskId/attempts', { config: requirePrincipal('mission.task.record_attempt') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { taskId } = req.params as { taskId: string };
      const body = (req.body ?? {}) as any;
      if (!body.outcome) throw new PublicHttpError(400, 'outcome is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.recordActionAttempt({ mission_task_id: taskId, ...body, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/evidence', { config: requirePrincipal('mission.evidence.link') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.evidence_id) throw new PublicHttpError(400, 'evidence_id is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.linkEvidence({ mission_id: missionId, evidence_id: body.evidence_id, actor_id: req.principal!.actorId });
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/outcome', { config: requirePrincipal('mission.outcome.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.result || !body.summary) throw new PublicHttpError(400, 'result, summary are required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await missionService.recordOutcome({ mission_id: missionId, ...body, actor_id: req.principal!.actorId });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/settlement', { config: requirePrincipal('mission.settlement.record') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.settlement) throw new PublicHttpError(400, 'settlement is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      await missionService.recordSettlement({ mission_id: missionId, settlement: body.settlement, actor_id: req.principal!.actorId });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/complete', { config: requirePrincipal('mission.complete') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.completeMission({ mission_id: missionId, actor_id: req.principal!.actorId, reason: body.reason });
    })
  );

  fastify.post('/api/civilization/missions/:missionId/settle', { config: requirePrincipal('mission.settle') }, async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.reason) throw new PublicHttpError(400, 'reason is required');
      // AUD-004: actor_id is the AUTHENTICATED principal, never a body field.
      return missionService.settleMission({ mission_id: missionId, actor_id: req.principal!.actorId, reason: body.reason });
    })
  );
}
