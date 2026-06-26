import type { FastifyReply, FastifyRequest } from 'fastify';

const DEV_API_KEY = 'dev-api-key';

export function isProductionEnv(env: NodeJS.ProcessEnv = process.env): boolean {
  const agentcoEnv = (env.AGENTCO_ENV || '').toLowerCase();
  const nodeEnv = (env.NODE_ENV || '').toLowerCase();
  return agentcoEnv === 'production' || agentcoEnv === 'staging' || nodeEnv === 'production';
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
