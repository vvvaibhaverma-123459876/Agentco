import type { FastifyReply, FastifyRequest } from 'fastify';

const DEV_API_KEY = 'dev-api-key';

export function isProductionEnv(env: NodeJS.ProcessEnv = process.env): boolean {
  return env.AGENTCO_ENV === 'production';
}

function hasDevPassword(value: string | undefined): boolean {
  return Boolean(value && /:\/\/[^:]+:password@/.test(value));
}

export function assertProductionSecrets(env: NodeJS.ProcessEnv = process.env): void {
  if (!isProductionEnv(env)) return;

  const failures: string[] = [];
  if (!env.AGENTCO_API_KEY || env.AGENTCO_API_KEY === DEV_API_KEY) failures.push('AGENTCO_API_KEY');
  if (!env.EVENT_BUS_SIGNING_KEY || env.EVENT_BUS_SIGNING_KEY === 'dev-key-replace-in-production') failures.push('EVENT_BUS_SIGNING_KEY');
  if (!env.EVENT_BUS_HMAC_KEY || env.EVENT_BUS_HMAC_KEY === 'dev-insecure-key') failures.push('EVENT_BUS_HMAC_KEY');
  if (!env.JWT_SECRET || env.JWT_SECRET === 'change-me-generate-with-openssl-rand-hex-64') failures.push('JWT_SECRET');
  if (!env.VAULT_TOKEN || env.VAULT_TOKEN === 'root') failures.push('VAULT_TOKEN');
  if (hasDevPassword(env.DATABASE_URL)) failures.push('DATABASE_URL');
  if (hasDevPassword(env.AGENTCO_TEST_DATABASE_URL)) failures.push('AGENTCO_TEST_DATABASE_URL');
  if (env.RESERVE_SIGNING_KEY === 'dev-insecure-key') failures.push('RESERVE_SIGNING_KEY');

  if (failures.length > 0) {
    throw new Error(
      `Refusing to start in production with dev-default or missing secrets: ${failures.join(', ')}`
    );
  }
}

export async function requireApiKey(req: FastifyRequest, reply: FastifyReply) {
  const configured = process.env.AGENTCO_API_KEY || DEV_API_KEY;
  const provided = req.headers['x-agentco-api-key'];
  const key = Array.isArray(provided) ? provided[0] : provided;
  if (key !== configured) {
    return reply.status(401).send({ error: 'valid x-agentco-api-key required' });
  }
}

export type AgentcoRole =
  | 'agent'
  | 'resolver_service'
  | 'reserve_issuer'
  | 'human_reviewer'
  | 'auditor'
  | 'operator'
  | 'admin'
  | 'service';

const ROLE_SCOPES: Record<AgentcoRole, string[]> = {
  agent: ['claims:register', 'trust:read'],
  resolver_service: ['claims:resolve', 'claims:audit', 'trust:read'],
  reserve_issuer: ['credentials:issue', 'credentials:verify', 'trust:read'],
  human_reviewer: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate'],
  auditor: ['audit:read', 'claims:audit', 'credentials:verify', 'trust:read'],
  operator: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate', 'audit:read'],
  admin: ['config:manage', 'audit:read'],
  service: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate', 'claims:register', 'audit:read'],
};

export const privilegedSecurityEvents: Array<Record<string, unknown>> = [];

function header(req: FastifyRequest, name: string): string {
  const value = req.headers[name.toLowerCase()];
  return String(Array.isArray(value) ? value[0] : value ?? '');
}

export function roleFromRequest(req: FastifyRequest): AgentcoRole | undefined {
  const role = header(req, 'x-agentco-role') as AgentcoRole;
  return Object.prototype.hasOwnProperty.call(ROLE_SCOPES, role) ? role : undefined;
}

export function auditSecurityDecision(req: FastifyRequest, decision: string, reason: string): void {
  privilegedSecurityEvents.push({
    decision,
    reason,
    role: header(req, 'x-agentco-role') || 'none',
    path: req.url,
    method: req.method,
    createdAt: new Date().toISOString(),
  });
}

export function requireScope(scope: string) {
  return async function scopedAuth(req: FastifyRequest, reply: FastifyReply) {
    const keyResult = await requireApiKey(req, reply);
    if (reply.sent) return keyResult;
    const role = roleFromRequest(req);
    if (!role) {
      auditSecurityDecision(req, 'rejected', 'missing_or_invalid_role');
      return reply.status(403).send({ error: 'valid x-agentco-role required' });
    }
    if (!ROLE_SCOPES[role].includes(scope)) {
      auditSecurityDecision(req, 'rejected', `missing_scope:${scope}`);
      return reply.status(403).send({ error: `role ${role} lacks scope ${scope}` });
    }
  };
}

export function assertAgentNotResolvingOwnClaim(agentId: string | undefined, resolverId: string | undefined): void {
  if (agentId && resolverId && agentId === resolverId) {
    throw new Error('agent cannot resolve own claim');
  }
}
