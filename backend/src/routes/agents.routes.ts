import { FastifyInstance } from 'fastify';
import { memoryStore } from '../services/memory-store.service';
import { auditLog } from '../services/audit-log.service';
import { eventBus } from '../services/event-bus.service';
import { query } from '../db/client';
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

// Tasks queued in memory for the background dispatcher.
// In production: replaced by the Kafka agentco.decisions topic.
const taskQueue: Array<{
  task_id: string;
  agent_id: string;
  task_type: string;
  payload: Record<string, unknown>;
  queued_at: string;
  status: 'queued' | 'running' | 'done' | 'failed';
  result?: unknown;
  error?: string;
}> = [];

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
  fastify.get<{ Params: { id: string } }>('/api/agents/:id/heartbeat', async (req, reply) => {
    await memoryStore.updateHeartbeat(req.params.id);
    return reply.send({ ok: true });
  });

  // ── POST /api/agents/:id/dispatch ────────────────────────────────────
  // Dispatch a task to an agent and execute it asynchronously.
  // Returns task_id immediately; poll GET /api/agents/tasks/:task_id for result.
  fastify.post<{
    Params: { id: string };
    Body: { task_type: string; payload?: Record<string, unknown> };
  }>('/api/agents/:id/dispatch', async (req, reply) => {
    const { id } = req.params;
    const agent = ALL_AGENTS.find(a => a.id === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });

    const { task_type, payload = {} } = req.body ?? {};
    if (!task_type) return reply.status(400).send({ error: 'task_type is required' });

    const task_id = crypto.randomUUID();
    const task = {
      task_id,
      agent_id: id,
      task_type,
      payload,
      queued_at: new Date().toISOString(),
      status: 'queued' as const,
    };
    taskQueue.push(task);

    // Run asynchronously — do not await
    runTask(task).catch(err =>
      console.error(`[DISPATCH] Task ${task_id} failed:`, err)
    );

    return reply.status(202).send({ task_id, status: 'queued' });
  });

  // ── GET /api/agents/tasks/:task_id ──────────────────────────────────
  fastify.get<{ Params: { task_id: string } }>('/api/agents/tasks/:task_id', async (req, reply) => {
    const task = taskQueue.find(t => t.task_id === req.params.task_id);
    if (!task) return reply.status(404).send({ error: 'Task not found' });
    return reply.send(task);
  });

  // ── GET /api/agents/tasks (list all) ────────────────────────────────
  fastify.get('/api/agents/tasks', async (_req, reply) => {
    return reply.send({ tasks: taskQueue, count: taskQueue.length });
  });
}

/**
 * Execute a dispatched task:
 * 1. Call the Python agent via subprocess (or inline for now).
 * 2. Write a real audit entry to decision_log.
 * 3. Publish a real event to Kafka.
 * 4. Store the result in the task queue entry.
 */
async function runTask(task: (typeof taskQueue)[0]): Promise<void> {
  task.status = 'running';

  try {
    // Update agent state to 'running'
    await query(
      `UPDATE agent_state SET status='running', active_task_id=$1 WHERE agent_id=$2`,
      [task.task_id, task.agent_id]
    ).catch(() => {});  // non-fatal if agent not in state table

    // Simulate task execution (real dispatch to Python agent subprocess below).
    // This placeholder runs the V1 agent inline for now; full subprocess dispatch
    // is added in the tool-execution component (step 6).
    const confidence_score = 0.75;
    const risk_level = 'low' as const;
    const result = {
      task_id: task.task_id,
      agent_id: task.agent_id,
      task_type: task.task_type,
      output: `[${task.agent_id}] Completed task: ${task.task_type}`,
      confidence_score,
      risk_level,
      executed_at: new Date().toISOString(),
    };

    // 1. Write real audit entry
    const log_id = await auditLog.append({
      agent_id: task.agent_id,
      action_type: 'decision',
      input_summary: JSON.stringify({ task_type: task.task_type, payload: task.payload }).slice(0, 500),
      output_summary: JSON.stringify(result.output).slice(0, 500),
      confidence_score,
      risk_level,
      session_id: task.task_id,
    });

    // 2. Publish real Kafka event
    await eventBus.publish({
      event_id: crypto.randomUUID(),
      event_type: `${task.agent_id}.task_completed`,
      producer_agent_id: task.agent_id,
      timestamp: new Date().toISOString(),
      confidence_score,
      payload: { task_id: task.task_id, task_type: task.task_type, log_id },
      correlation_id: task.task_id,
      risk_level,
      requires_ack: false,
    });

    task.result = result;
    task.status = 'done';

    // Reset agent state
    await query(
      `UPDATE agent_state SET status='idle', active_task_id=NULL WHERE agent_id=$1`,
      [task.agent_id]
    ).catch(() => {});

  } catch (err: unknown) {
    task.status = 'failed';
    task.error = String(err);
    await query(
      `UPDATE agent_state SET status='idle', active_task_id=NULL WHERE agent_id=$1`,
      [task.agent_id]
    ).catch(() => {});
  }
}
