import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';

const MAX_BODY_SIZE = 10 * 1024; // 10KB
const RATE_LIMIT_WINDOW = 60000; // 1 minute
const RATE_LIMIT_MAX = 100; // max requests per window per entity

interface RateLimitEntry {
  count: number;
  resetTime: number;
}

const rateLimitMap = new Map<string, RateLimitEntry>();

function validateBodySize(req: FastifyRequest): boolean {
  const bodySize = JSON.stringify(req.body).length;
  return bodySize <= MAX_BODY_SIZE;
}

function checkRateLimit(entityId: string): boolean {
  const now = Date.now();
  const entry = rateLimitMap.get(entityId);

  if (!entry || entry.resetTime < now) {
    rateLimitMap.set(entityId, {
      count: 1,
      resetTime: now + RATE_LIMIT_WINDOW,
    });
    return true;
  }

  if (entry.count >= RATE_LIMIT_MAX) {
    return false;
  }

  entry.count++;
  return true;
}

export async function civilizationRequestValidator(
  fastify: FastifyInstance
): Promise<void> {
  fastify.addHook('preHandler', async (req: FastifyRequest, reply: FastifyReply) => {
    // Only validate civilization endpoints
    if (!req.url.startsWith('/api/civilization/')) {
      return;
    }

    // Check body size (for POST/PUT requests)
    if (['POST', 'PUT'].includes(req.method)) {
      if (!validateBodySize(req)) {
        return reply.status(413).send({
          error: 'Payload too large',
          maxSize: MAX_BODY_SIZE,
        });
      }
    }

    // Check rate limit by entity ID if provided
    const entityId = (req.body as any)?.entityId || (req.body as any)?.creatorEntityId;
    if (entityId) {
      if (!checkRateLimit(entityId)) {
        return reply.status(429).send({
          error: 'Too many requests',
          retryAfter: RATE_LIMIT_WINDOW / 1000,
        });
      }
    }
  });
}

export function validateGovernanceDecision(payload: any): string[] {
  const errors: string[] = [];

  if (!payload.decision_type) {
    errors.push('decision_type is required');
  } else if (!['create_institution', 'retire_institution', 'approve_high_risk_output', 'change_reputation_weights', 'change_contract'].includes(payload.decision_type)) {
    errors.push('decision_type must be one of: create_institution, retire_institution, approve_high_risk_output, change_reputation_weights, change_contract');
  }

  if (!payload.proposer_entity_id) {
    errors.push('proposer_entity_id is required');
  }

  if (!payload.payload || typeof payload.payload !== 'object') {
    errors.push('payload must be a non-empty object');
  }

  return errors;
}

export function validateInstitutionContract(contract: any): string[] {
  const errors: string[] = [];
  const required = [
    'institution_name', 'accepted_inputs', 'produced_outputs',
    'verification_required', 'required_external_reviewer',
    'failure_conditions', 'escalation_target', 'reputation_metric',
  ];

  for (const field of required) {
    if (!contract[field]) {
      errors.push(`${field} is required`);
    }
  }

  if (contract.institution_name === contract.required_external_reviewer) {
    errors.push('required_external_reviewer must differ from institution_name');
  }

  return errors;
}
