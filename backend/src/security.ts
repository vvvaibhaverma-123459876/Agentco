import type { FastifyReply, FastifyRequest } from 'fastify';

const DEV_API_KEY = 'dev-api-key';

export interface Principal {
  principal_id: string;
  scopes: string[];
  auth_method: 'service_key' | 'dev_api_key';
}

interface ServiceKeyConfig {
  key: string;
  scopes: string[];
}

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
  if (!env.AGENTCO_SERVICE_KEYS_JSON) failures.push('AGENTCO_SERVICE_KEYS_JSON');
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

export function parseServiceKeys(env: NodeJS.ProcessEnv = process.env): Record<string, ServiceKeyConfig> {
  const raw = env.AGENTCO_SERVICE_KEYS_JSON;
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as Record<string, ServiceKeyConfig>;
    for (const [principalId, config] of Object.entries(parsed)) {
      if (!config || typeof config.key !== 'string' || !Array.isArray(config.scopes)) {
        throw new Error(`invalid service key config for ${principalId}`);
      }
    }
    return parsed;
  } catch (error) {
    throw new Error(`Invalid AGENTCO_SERVICE_KEYS_JSON: ${error instanceof Error ? error.message : String(error)}`);
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
  agent: ['claims:register', 'trust:read', 'task:read', 'read:*'],
  resolver_service: ['claims:resolve', 'claims:audit', 'prediction:resolve', 'evidence:write', 'trust:read'],
  reserve_issuer: ['credentials:issue', 'credentials:verify', 'credential:issue', 'credential:verify', 'trust:read'],
  human_reviewer: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate'],
  auditor: ['audit:read', 'claims:audit', 'credentials:verify', 'credential:verify', 'trust:read', 'task:read', 'read:*'],
  operator: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate', 'governance:*', 'audit:read', 'task:dispatch', 'task:read', 'task:cancel'],
  admin: ['config:manage', 'admin:*', 'audit:read', 'governance:*', 'task:dispatch', 'task:read', 'task:cancel', 'credential:issue', 'credential:verify'],
  service: ['institutions:mutate', 'outputs:mutate', 'reviews:mutate', 'governance:mutate', 'claims:register', 'audit:read', 'task:dispatch', 'task:read', 'task:cancel'],
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
    principal_id: (req as FastifyRequest & { principal?: Principal }).principal?.principal_id ?? 'none',
    path: req.url,
    method: req.method,
    createdAt: new Date().toISOString(),
  });
}

function providedKey(req: FastifyRequest): string {
  return header(req, 'x-agentco-service-key') || header(req, 'x-agentco-api-key');
}

export function authenticateRequest(req: FastifyRequest, env: NodeJS.ProcessEnv = process.env): Principal | undefined {
  const key = providedKey(req);
  if (!key) return undefined;

  const serviceKeys = parseServiceKeys(env);
  for (const [principalId, config] of Object.entries(serviceKeys)) {
    if (key === config.key) {
      return { principal_id: principalId, scopes: config.scopes, auth_method: 'service_key' };
    }
  }

  if (!isProductionEnv(env) && key === (env.AGENTCO_API_KEY || DEV_API_KEY)) {
    const role = roleFromRequest(req);
    if (!role) return undefined;
    return {
      principal_id: `dev-role:${role}`,
      scopes: ROLE_SCOPES[role],
      auth_method: 'dev_api_key',
    };
  }
  return undefined;
}

export function hasScope(principal: Principal, requiredScope: string): boolean {
  return principal.scopes.some((scope) => (
    scope === requiredScope
    || scope === '*'
    || (scope.endsWith(':*') && requiredScope.startsWith(scope.slice(0, -1)))
  ));
}

export function requireScope(scope: string) {
  return async function scopedAuth(req: FastifyRequest, reply: FastifyReply) {
    const principal = authenticateRequest(req);
    if (!principal) {
      auditSecurityDecision(req, 'rejected', 'missing_or_invalid_principal');
      return reply.status(401).send({ error: 'valid service key required' });
    }
    (req as FastifyRequest & { principal?: Principal }).principal = principal;
    if (!hasScope(principal, scope)) {
      auditSecurityDecision(req, 'rejected', `missing_scope:${scope}`);
      return reply.status(403).send({ error: `principal ${principal.principal_id} lacks scope ${scope}` });
    }
  };
}

export function assertAgentNotResolvingOwnClaim(agentId: string | undefined, resolverId: string | undefined): void {
  if (agentId && resolverId && agentId === resolverId) {
    throw new Error('agent cannot resolve own claim');
  }
}

export async function checkEmergencyShutdown(): Promise<boolean> {
  try {
    const fs = require('fs');
    const path = require('path');
    const yaml = require('js-yaml');
    const controlsPath = path.resolve(__dirname, '..', '..', 'civilization', 'controls.yaml');
    const content = fs.readFileSync(controlsPath, 'utf-8');
    const controls = yaml.load(content) as Record<string, unknown>;
    return Boolean(controls.emergency_shutdown_flag);
  } catch {
    return false;
  }
}

export function requireEmergencyShutdownOff(riskLevel: 'low' | 'medium' | 'high' = 'medium') {
  return async function emergencyCheck(req: FastifyRequest, reply: FastifyReply) {
    const shutdown = await checkEmergencyShutdown();
    if (shutdown && riskLevel !== 'low') {
      auditSecurityDecision(req, 'rejected', `emergency_shutdown_active:${riskLevel}_risk`);
      return reply.status(503).send({
        error: 'emergency shutdown active',
        risk_level: riskLevel,
        message: `${riskLevel}-risk operations are blocked during emergency shutdown`,
      });
    }
  };
}
