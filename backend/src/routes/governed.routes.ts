import type { FastifyInstance, FastifyReply, FastifyRequest } from 'fastify';
import { randomUUID } from 'crypto';
import { assertAgentNotResolvingOwnClaim, privilegedSecurityEvents, requireScope } from '../security';

type Entity = Record<string, unknown> & { id: string };
type MutationResult = { statusCode: number; body: Entity | Record<string, unknown> };

const VALID_ROLES = new Set(['member', 'contributor', 'producer', 'reviewer', 'auditor', 'adversary', 'improver', 'lead', 'engineer']);

const institutions = new Map<string, Entity>();
const institutionAgents = new Map<string, Map<string, Entity>>();
const outputs = new Map<string, Entity>();
const reviews = new Map<string, Entity>();
const governanceDecisions = new Map<string, Entity>();
const claims = new Map<string, Entity>();
const credentials = new Map<string, Entity>();
const auditEvents: Entity[] = [];
const idempotency = new Map<string, MutationResult>();

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

function traceId(req: FastifyRequest): string {
  const header = req.headers['x-request-id'];
  return Array.isArray(header) ? header[0] : header || randomUUID();
}

function audit(req: FastifyRequest, action: string, entityType: string, entityId: string): Entity {
  const event = {
    id: randomUUID(),
    action,
    entityType,
    entityId,
    traceId: traceId(req),
    createdAt: new Date().toISOString(),
  };
  auditEvents.push(event);
  return event;
}

function mutation(req: FastifyRequest, reply: FastifyReply, run: () => MutationResult) {
  const keyHeader = req.headers['idempotency-key'];
  const key = Array.isArray(keyHeader) ? keyHeader[0] : keyHeader;
  const methodUrlKey = key ? `${req.method}:${req.url}:${key}` : '';
  if (methodUrlKey && idempotency.has(methodUrlKey)) {
    const cached = idempotency.get(methodUrlKey)!;
    return reply.status(cached.statusCode).send(cached.body);
  }
  const result = run();
  if (methodUrlKey) idempotency.set(methodUrlKey, result);
  return reply.status(result.statusCode).send(result.body);
}

function notFound(reply: FastifyReply, entity: string) {
  return reply.status(404).send({ error: `${entity} not found` });
}

export async function governedRoutes(app: FastifyInstance) {
  app.post('/institutions', { preHandler: requireScope('institutions:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const body = bodyOf(req);
    const id = String(body.id ?? randomUUID());
    const inst = { id, name: String(body.name ?? 'Institution'), status: 'active', createdAt: new Date().toISOString() };
    institutions.set(id, inst);
    audit(req, 'institution_created', 'institution', id);
    return { statusCode: 201, body: inst };
  }));

  app.get('/institutions/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    const inst = institutions.get(id);
    return inst ? inst : notFound(reply, 'institution');
  });

  app.post('/institutions/:id/agents', { preHandler: requireScope('institutions:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const { id } = req.params as { id: string };
    if (!institutions.has(id)) return { statusCode: 404, body: { error: 'institution not found' } };
    const body = bodyOf(req);
    const role = String(body.role ?? '');
    if (!VALID_ROLES.has(role)) return { statusCode: 400, body: { error: 'invalid role' } };
    const agentId = String(body.agent_id ?? body.agentId ?? randomUUID());
    const agents = institutionAgents.get(id) ?? new Map<string, Entity>();
    const agent = { id: agentId, institutionId: id, role, status: 'active' };
    agents.set(agentId, agent);
    institutionAgents.set(id, agents);
    audit(req, 'institution_agent_added', 'agent', agentId);
    return { statusCode: 201, body: agent };
  }));

  app.delete('/institutions/:id/agents/:agent_id', { preHandler: requireScope('institutions:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const { id, agent_id } = req.params as { id: string; agent_id: string };
    institutionAgents.get(id)?.delete(agent_id);
    audit(req, 'institution_agent_removed', 'agent', agent_id);
    return { statusCode: 200, body: { id: agent_id, removed: true } };
  }));

  app.get('/institutions/:id/reputation', async (req, reply) => {
    const { id } = req.params as { id: string };
    if (!institutions.has(id)) return notFound(reply, 'institution');
    return { institution_id: id, reputation_score: null, source: 'calibrated_evidence_only' };
  });

  app.get('/institutions/:id/memory', async (req, reply) => {
    const { id } = req.params as { id: string };
    if (!institutions.has(id)) return notFound(reply, 'institution');
    return { institution_id: id, events: auditEvents.filter((e) => e.entityId === id || e.entityType === 'institution') };
  });

  app.post('/outputs', { preHandler: requireScope('outputs:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const body = bodyOf(req);
    const id = String(body.id ?? randomUUID());
    const output = { id, status: 'proposed', ...body };
    outputs.set(id, output);
    audit(req, 'output_created', 'output', id);
    return { statusCode: 201, body: output };
  }));

  app.get('/outputs/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    return outputs.get(id) ?? notFound(reply, 'output');
  });

  app.post('/reviews/:id/transition', { preHandler: requireScope('reviews:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const { id } = req.params as { id: string };
    const body = bodyOf(req);
    const review = reviews.get(id) ?? { id, status: 'proposed' };
    review.status = String(body.status ?? 'under_review');
    reviews.set(id, review);
    audit(req, 'review_transitioned', 'review', id);
    return { statusCode: 200, body: review };
  }));

  app.get('/reviews/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    return reviews.get(id) ?? notFound(reply, 'review');
  });

  app.post('/governance/decisions', { preHandler: requireScope('governance:mutate') }, async (req, reply) => mutation(req, reply, () => {
    const id = randomUUID();
    const decision = { id, status: 'proposed', ...bodyOf(req) };
    governanceDecisions.set(id, decision);
    audit(req, 'governance_decision', 'governance_decision', id);
    return { statusCode: 201, body: decision };
  }));

  for (const action of ['approve', 'execute', 'rollback'] as const) {
    app.post(`/governance/decisions/:id/${action}`, { preHandler: requireScope('governance:mutate') }, async (req, reply) => mutation(req, reply, () => {
      const { id } = req.params as { id: string };
      const decision = governanceDecisions.get(id);
      if (!decision) return { statusCode: 404, body: { error: 'governance decision not found' } };
      decision.status = action === 'approve' ? 'approved' : action === 'execute' ? 'executed' : 'rolled_back';
      audit(req, `governance_${action}`, 'governance_decision', id);
      return { statusCode: 200, body: decision };
    }));
  }

  app.get('/governance/decisions/:id', async (req, reply) => {
    const { id } = req.params as { id: string };
    return governanceDecisions.get(id) ?? notFound(reply, 'governance decision');
  });

  app.post('/claims/register', { preHandler: requireScope('claims:register') }, async (req, reply) => mutation(req, reply, () => {
    const id = randomUUID();
    const claim = { id, status: 'registered', independence_status: 'unresolved', ...bodyOf(req) };
    claims.set(id, claim);
    audit(req, 'claim_registered', 'claim', id);
    return { statusCode: 201, body: claim };
  }));

  app.post('/claims/:id/resolve', { preHandler: requireScope('claims:resolve') }, async (req, reply) => mutation(req, reply, () => {
    const { id } = req.params as { id: string };
    const claim = claims.get(id);
    if (!claim) return { statusCode: 404, body: { error: 'claim not found' } };
    try {
      assertAgentNotResolvingOwnClaim(String(claim.producing_agent_id ?? claim.agent_id ?? ''), String(bodyOf(req).resolver_id ?? ''));
    } catch (err) {
      return { statusCode: 403, body: { error: (err as Error).message } };
    }
    claim.status = 'resolved';
    claim.independence_status = 'accepted';
    audit(req, 'claim_resolved', 'claim', id);
    return { statusCode: 200, body: claim };
  }));

  app.get('/claims/:id/audit', async (req, reply) => {
    const { id } = req.params as { id: string };
    return { claim_id: id, events: auditEvents.filter((e) => e.entityId === id) };
  });

  app.get('/agents/:id/trust', async (req) => {
    const { id } = req.params as { id: string };
    return { agent_id: id, trust_source: 'resolved_independent_claims', trust_score: null };
  });

  app.post('/credentials/issue', { preHandler: requireScope('credentials:issue') }, async (req, reply) => mutation(req, reply, () => {
    const id = randomUUID();
    const credential = { id, status: 'issued', recomputable: true, ...bodyOf(req) };
    credentials.set(id, credential);
    audit(req, 'credential_issued', 'credential', id);
    return { statusCode: 201, body: credential };
  }));

  app.get('/credentials/:id/verify', async (req, reply) => {
    const { id } = req.params as { id: string };
    if (!credentials.has(id)) return notFound(reply, 'credential');
    return { credential_id: id, valid: true, verification: 'signature_and_recomputation_stub' };
  });

  app.get('/audit/mutations', async () => ({ events: auditEvents }));
  app.get('/audit/security', async () => ({ events: privilegedSecurityEvents }));
}
