import { FastifyInstance } from 'fastify';
import { memoryStore } from '../services/memory-store.service';
import { requireScope, requireEmergencyShutdownOff } from '../security';
import { cancelTask, createTask, getTask, listTasks } from '../services/task-dispatch.service';

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
  fastify.get<{ Params: { id: string } }>('/api/agents/:id/heartbeat', { preHandler: requireScope('task:read') }, async (req, reply) => {
    await memoryStore.updateHeartbeat(req.params.id);
    return reply.send({ ok: true });
  });

  // ── POST /api/agents/:id/dispatch ────────────────────────────────────
  // Dispatch a task to an agent durably. A worker leases and executes it.
  // Returns task_id immediately; poll GET /api/agents/tasks/:task_id for result.
  fastify.post<{
    Params: { id: string };
    Body: { task_type: string; payload?: Record<string, unknown>; correlation_id?: string };
  }>('/api/agents/:id/dispatch', { preHandler: [requireScope('task:dispatch'), requireEmergencyShutdownOff('high')] }, async (req, reply) => {
    const { id } = req.params;
    const agent = ALL_AGENTS.find(a => a.id === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });

    const { task_type, payload = {}, correlation_id } = req.body ?? {};
    if (!task_type) return reply.status(400).send({ error: 'task_type is required' });

    const task = await createTask(id, task_type, payload, { correlationId: correlation_id });
    return reply.status(202).send({ task_id: task.task_id, status: task.status });
  });

  // ── GET /api/agents/tasks/:task_id ──────────────────────────────────
  fastify.get<{ Params: { task_id: string } }>('/api/agents/tasks/:task_id', { preHandler: requireScope('task:read') }, async (req, reply) => {
    const task = await getTask(req.params.task_id);
    if (!task) return reply.status(404).send({ error: 'Task not found' });
    return reply.send(task);
  });

  // ── GET /api/agents/tasks (list all) ────────────────────────────────
  fastify.get<{ Querystring: { agent_id?: string; status?: string } }>('/api/agents/tasks', { preHandler: requireScope('task:read') }, async (req, reply) => {
    const tasks = await listTasks({ agentId: req.query.agent_id, status: req.query.status });
    return reply.send({ tasks, count: tasks.length });
  });

  fastify.post<{ Params: { task_id: string } }>('/api/agents/tasks/:task_id/cancel', { preHandler: requireScope('task:cancel') }, async (req, reply) => {
    const task = await cancelTask(req.params.task_id);
    if (!task) return reply.status(409).send({ error: 'Task not cancellable or not found' });
    return reply.send(task);
  });
}
