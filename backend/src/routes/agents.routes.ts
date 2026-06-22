import { FastifyInstance } from 'fastify';
import { memoryStore } from '../services/memory-store.service';
import { auditLog } from '../services/audit-log.service';
import { eventBus } from '../services/event-bus.service';
import { learningService } from '../services/learning.service';
import { query } from '../db/client';
import { requireApiKey } from '../security';
import crypto from 'crypto';

// Model resolved from local model-tier map (matches runtime/base_agent/model_tiers.py).
// No cloud model ids here.
const AGENT_MODEL: Record<string, string> = {
  'ceo-agent':    'phi4',
  'cfo-agent':    'phi4',
  'coo-agent':    'phi4',
  'synthesis-agent':   'phi4',
  'calibration-reasoner': 'phi4',
  'coder-agent':   'qwen2.5-coder:7b',
  'reviewer-agent':'qwen2.5-coder:7b',
  // all others resolve to standard tier
};
function modelFor(agentId: string): string {
  return AGENT_MODEL[agentId] ?? 'qwen2.5:7b';
}

const ALL_AGENTS = [
  { id: 'ceo-agent',         department: 'executive' },
  { id: 'cfo-agent',         department: 'executive' },
  { id: 'coo-agent',         department: 'executive' },
  { id: 'pm-agent',          department: 'product' },
  { id: 'research-agent',    department: 'product' },
  { id: 'prioritizer-agent', department: 'product' },
  { id: 'architect-agent',   department: 'engineering' },
  { id: 'coder-agent',       department: 'engineering' },
  { id: 'reviewer-agent',    department: 'engineering' },
  { id: 'devops-agent',      department: 'engineering' },
  { id: 'ux-agent',          department: 'design' },
  { id: 'brand-agent',       department: 'design' },
  { id: 'ab-agent',          department: 'design' },
  { id: 'sdr-agent',         department: 'sales' },
  { id: 'ae-agent',          department: 'sales' },
  { id: 'revops-agent',      department: 'sales' },
  { id: 'content-agent',     department: 'marketing' },
  { id: 'seo-agent',         department: 'marketing' },
  { id: 'ads-agent',         department: 'marketing' },
  { id: 'analytics-agent',   department: 'marketing' },
  { id: 'support-agent',     department: 'customer_experience' },
  { id: 'success-agent',     department: 'customer_experience' },
  { id: 'voice-agent',       department: 'customer_experience' },
  { id: 'performance-agent', department: 'people_ops' },
  { id: 'recruiter-agent',   department: 'people_ops' },
  { id: 'config-agent',      department: 'people_ops' },
  { id: 'contract-agent',    department: 'legal' },
  { id: 'risk-agent',        department: 'legal' },
  { id: 'privacy-agent',     department: 'legal' },
];

export async function agentRoutes(fastify: FastifyInstance) {
  // ── GET /api/agents ──────────────────────────────────────────────────
  fastify.get('/api/agents', async (_req, reply) => {
    const agents = await Promise.all(
      ALL_AGENTS.map(async (a) => ({
        ...a,
        model: modelFor(a.id),
        state: await memoryStore.getAgentState(a.id) ?? {
          status: 'idle', lifecycle_state: 'production',
        },
      }))
    );
    return reply.send({ agents, count: agents.length });
  });

  // ── GET /api/agents/:id ──────────────────────────────────────────────
  fastify.get<{ Params: { id: string } }>('/api/agents/:id', async (req, reply) => {
    const { id } = req.params;
    const agent = ALL_AGENTS.find(a => a.id === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });
    const state = await memoryStore.getAgentState(id);
    return reply.send({ ...agent, model: modelFor(id), state });
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
    const agent = ALL_AGENTS.find(a => a.id === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });

    const { task_type, payload = {} } = req.body ?? {};
    if (!task_type) return reply.status(400).send({ error: 'task_type is required' });

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
          error: err.message,
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
