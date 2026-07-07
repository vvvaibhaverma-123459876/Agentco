import { FastifyInstance } from 'fastify';
import { memoryStore } from '../services/memory-store.service';
import { auditLog } from '../services/audit-log.service';
import { eventBus } from '../services/event-bus.service';
import { learningService } from '../services/learning.service';
import { durableExecution } from '../services/durable-execution.service';
import { query } from '../db/client';
import { requireApiKey } from '../security';
import crypto from 'crypto';
import { assertAgentCanRunTask, listAgentRegistryWithIdentities } from '../agent-registry';

export async function agentRoutes(fastify: FastifyInstance) {
  // ── GET /api/agents ──────────────────────────────────────────────────
  fastify.get('/api/agents', async (_req, reply) => {
    const registry = await listAgentRegistryWithIdentities();
    const agents = await Promise.all(
      registry.map(async (agent) => ({
        id: agent.agentId,
        actor_id: agent.actorId,
        actor_status: agent.actorStatus,
        identity_status: agent.identityStatus,
        department: agent.department,
        runtime: {
          runtimeStatus: agent.runtimeStatus,
          allowedTaskTypes: agent.allowedTaskTypes,
          modelTier: agent.modelTier,
          capabilityTags: agent.capabilityTags,
        },
        model: agent.modelName,
        version: agent.version,
        state: await memoryStore.getAgentState(agent.agentId) ?? {
          status: 'idle', lifecycle_state: 'production',
        },
      }))
    );
    return reply.send({ agents, count: agents.length });
  });

  // ── GET /api/agents/:id ──────────────────────────────────────────────
  fastify.get<{ Params: { id: string } }>('/api/agents/:id', async (req, reply) => {
    const { id } = req.params;
    const agent = (await listAgentRegistryWithIdentities()).find(a => a.agentId === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });
    const state = await memoryStore.getAgentState(id);
    return reply.send({
      id: agent.agentId,
      actor_id: agent.actorId,
      actor_status: agent.actorStatus,
      identity_status: agent.identityStatus,
      department: agent.department,
      runtime: {
        runtimeStatus: agent.runtimeStatus,
        allowedTaskTypes: agent.allowedTaskTypes,
        modelTier: agent.modelTier,
        capabilityTags: agent.capabilityTags,
      },
      model: agent.modelName,
      version: agent.version,
      state,
    });
  });

  // ── GET /api/agents/:id/heartbeat ────────────────────────────────────
  fastify.get<{ Params: { id: string } }>('/api/agents/:id/heartbeat', { preHandler: requireApiKey }, async (req, reply) => {
    await memoryStore.updateHeartbeat(req.params.id);
    return reply.send({ ok: true });
  });

  // ── POST /api/agents/:id/dispatch ────────────────────────────────────
  // Dispatch a task to an agent and execute it asynchronously.
  // Returns task_id immediately; poll GET /api/agents/tasks/:task_id for result.
  fastify.post<{
    Params: { id: string };
    Body: { task_type: string; payload?: Record<string, unknown> };
  }>('/api/agents/:id/dispatch', { preHandler: requireApiKey }, async (req, reply) => {
    const { id } = req.params;
    const agent = (await listAgentRegistryWithIdentities()).find(a => a.agentId === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });

    const { task_type, payload = {} } = req.body ?? {};
    if (!task_type) return reply.status(400).send({ error: 'task_type is required' });
    try {
      assertAgentCanRunTask(id, task_type);
    } catch (error) {
      return reply.status(422).send({
        error: error instanceof Error ? error.message : String(error),
        status: 'unsupported',
      });
    }

    if (process.env.AGENTCO_REQUIRE_SCOPES === 'true') {
      const scopes = String(req.headers['x-agentco-scope'] ?? '').split(/\s+/);
      if (!scopes.includes('dispatch:write')) {
        return reply.status(403).send({ error: 'dispatch:write scope required' });
      }
    }

    const task = await durableExecution.enqueue(id, task_type, payload);

    // Capture learning signal for this dispatch decision
    learningService.captureSignal(
      id,
      'decision',
      {
        task_type,
        payload,
        agent_id: id,
        decision: `Dispatch task ${task_type}`,
        evidence: 'task enqueued successfully',
        confidence: 0.9,
      },
      `agent://dispatch/${task.task_id}`,
    );

    durableExecution.run(task.task_id).catch(err => {
      console.error(`[DISPATCH] Task ${task.task_id} failed:`, err);
      // Capture failure signal
      learningService.captureSignal(
        id,
        'outcome',
        {
          task_id: task.task_id,
          task_type,
          outcome: 'failed',
          error: 'Request failed',
          confidence: 0.8,
        },
        `agent://outcome/${task.task_id}`,
      );
    });

    return reply.status(202).send({ task_id: task.task_id, status: task.status });
  });

  // ── GET /api/agents/tasks/:task_id ──────────────────────────────────
  fastify.get<{ Params: { task_id: string } }>('/api/agents/tasks/:task_id', async (req, reply) => {
    const task = await durableExecution.get(req.params.task_id);
    if (!task) return reply.status(404).send({ error: 'Task not found' });
    return reply.send(task);
  });

  // ── GET /api/agents/tasks (list all) ────────────────────────────────
  fastify.get('/api/agents/tasks', async (_req, reply) => {
    const tasks = await durableExecution.list();
    return reply.send({ tasks, count: tasks.length });
  });
}
