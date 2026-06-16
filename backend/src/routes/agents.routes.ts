import { FastifyInstance } from 'fastify';
import { memoryStore } from '../services/memory-store.service';

const ALL_AGENTS = [
  { id: 'ceo-agent', department: 'executive', model: 'claude-opus-4-8' },
  { id: 'cfo-agent', department: 'executive', model: 'claude-sonnet-4-6' },
  { id: 'coo-agent', department: 'executive', model: 'claude-sonnet-4-6' },
  { id: 'pm-agent', department: 'product', model: 'claude-sonnet-4-6' },
  { id: 'research-agent', department: 'product', model: 'claude-sonnet-4-6' },
  { id: 'prioritizer-agent', department: 'product', model: 'claude-sonnet-4-6' },
  { id: 'architect-agent', department: 'engineering', model: 'claude-sonnet-4-6' },
  { id: 'coder-agent', department: 'engineering', model: 'claude-sonnet-4-6' },
  { id: 'reviewer-agent', department: 'engineering', model: 'claude-sonnet-4-6' },
  { id: 'devops-agent', department: 'engineering', model: 'claude-sonnet-4-6' },
  { id: 'ux-agent', department: 'design', model: 'claude-sonnet-4-6' },
  { id: 'brand-agent', department: 'design', model: 'claude-sonnet-4-6' },
  { id: 'ab-agent', department: 'design', model: 'claude-sonnet-4-6' },
  { id: 'sdr-agent', department: 'sales', model: 'claude-sonnet-4-6' },
  { id: 'ae-agent', department: 'sales', model: 'claude-sonnet-4-6' },
  { id: 'revops-agent', department: 'sales', model: 'claude-sonnet-4-6' },
  { id: 'content-agent', department: 'marketing', model: 'claude-sonnet-4-6' },
  { id: 'seo-agent', department: 'marketing', model: 'claude-sonnet-4-6' },
  { id: 'ads-agent', department: 'marketing', model: 'claude-sonnet-4-6' },
  { id: 'analytics-agent', department: 'marketing', model: 'claude-sonnet-4-6' },
  { id: 'support-agent', department: 'customer_experience', model: 'claude-sonnet-4-6' },
  { id: 'success-agent', department: 'customer_experience', model: 'claude-sonnet-4-6' },
  { id: 'voice-agent', department: 'customer_experience', model: 'claude-sonnet-4-6' },
  { id: 'performance-agent', department: 'people_ops', model: 'claude-sonnet-4-6' },
  { id: 'recruiter-agent', department: 'people_ops', model: 'claude-sonnet-4-6' },
  { id: 'config-agent', department: 'people_ops', model: 'claude-sonnet-4-6' },
  { id: 'contract-agent', department: 'legal', model: 'claude-sonnet-4-6' },
  { id: 'risk-agent', department: 'legal', model: 'claude-sonnet-4-6' },
  { id: 'privacy-agent', department: 'legal', model: 'claude-sonnet-4-6' },
];

export async function agentRoutes(fastify: FastifyInstance) {
  fastify.get('/api/agents', async (_req, reply) => {
    const agents = await Promise.all(
      ALL_AGENTS.map(async (a) => ({
        ...a,
        state: await memoryStore.getAgentState(a.id) ?? { status: 'idle', lifecycle_state: 'production' },
      }))
    );
    return reply.send({ agents, count: agents.length });
  });

  fastify.get<{ Params: { id: string } }>('/api/agents/:id', async (req, reply) => {
    const { id } = req.params;
    const agent = ALL_AGENTS.find(a => a.id === id);
    if (!agent) return reply.status(404).send({ error: 'Agent not found' });
    const state = await memoryStore.getAgentState(id);
    return reply.send({ ...agent, state });
  });

  fastify.get<{ Params: { id: string } }>('/api/agents/:id/heartbeat', async (req, reply) => {
    await memoryStore.updateHeartbeat(req.params.id);
    return reply.send({ ok: true });
  });
}
