import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { missionService, MissionStatus } from '../services/mission.service';
import { PublicHttpError, publicMessageForError, statusCodeForError } from '../http-errors';

/** Objective/goal/mission routes (build phase C5). */
export async function missionRoutes(fastify: FastifyInstance): Promise<void> {
  const handle = async (reply: FastifyReply, fn: () => Promise<unknown>, successCode = 200) => {
    try {
      return reply.status(successCode).send(await fn());
    } catch (error) {
      return reply.status(statusCodeForError(error)).send({ error: publicMessageForError(error) });
    }
  };

  fastify.post('/api/civilization/strategic-goals', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return missionService.createStrategicGoal(body);
    }, 201)
  );

  fastify.post('/api/civilization/missions', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return missionService.createMission(body);
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

  fastify.post('/api/civilization/missions/:missionId/dependencies', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.depends_on_mission_id) throw new PublicHttpError(400, 'depends_on_mission_id is required');
      await missionService.addDependency(missionId, body.depends_on_mission_id);
      return { added: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/transition', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.to_status) throw new PublicHttpError(400, 'to_status is required');
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      if (!body.reason) throw new PublicHttpError(400, 'reason is required');
      return missionService.transitionMission({
        mission_id: missionId, to_status: body.to_status as MissionStatus,
        actor_id: body.actor_id, reason: body.reason, block_reason: body.block_reason,
      });
    })
  );

  fastify.post('/api/civilization/missions/:missionId/workstreams', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return missionService.addWorkstream({ mission_id: missionId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/workstreams/:workstreamId/tasks', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { workstreamId } = req.params as { workstreamId: string };
      const body = (req.body ?? {}) as any;
      if (!body.title) throw new PublicHttpError(400, 'title is required');
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      return missionService.addTask({ workstream_id: workstreamId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/workstreams/:workstreamId/complete', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { workstreamId } = req.params as { workstreamId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id) throw new PublicHttpError(400, 'actor_id is required');
      await missionService.completeWorkstream({ workstream_id: workstreamId, actor_id: body.actor_id, status: body.status });
      return { completed: true };
    })
  );

  fastify.post('/api/civilization/mission-tasks/:taskId/attempts', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { taskId } = req.params as { taskId: string };
      const body = (req.body ?? {}) as any;
      if (!body.outcome || !body.actor_id) throw new PublicHttpError(400, 'outcome and actor_id are required');
      return missionService.recordActionAttempt({ mission_task_id: taskId, ...body });
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/evidence', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.evidence_id || !body.actor_id) throw new PublicHttpError(400, 'evidence_id and actor_id are required');
      return missionService.linkEvidence({ mission_id: missionId, evidence_id: body.evidence_id, actor_id: body.actor_id });
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/outcome', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.result || !body.summary || !body.actor_id) throw new PublicHttpError(400, 'result, summary, actor_id are required');
      await missionService.recordOutcome({ mission_id: missionId, ...body });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/settlement', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.settlement || !body.actor_id) throw new PublicHttpError(400, 'settlement and actor_id are required');
      await missionService.recordSettlement({ mission_id: missionId, settlement: body.settlement, actor_id: body.actor_id });
      return { recorded: true };
    }, 201)
  );

  fastify.post('/api/civilization/missions/:missionId/complete', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id || !body.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      return missionService.completeMission({ mission_id: missionId, actor_id: body.actor_id, reason: body.reason });
    })
  );

  fastify.post('/api/civilization/missions/:missionId/settle', async (req: FastifyRequest, reply: FastifyReply) =>
    handle(reply, async () => {
      const { missionId } = req.params as { missionId: string };
      const body = (req.body ?? {}) as any;
      if (!body.actor_id || !body.reason) throw new PublicHttpError(400, 'actor_id and reason are required');
      return missionService.settleMission({ mission_id: missionId, actor_id: body.actor_id, reason: body.reason });
    })
  );
}
