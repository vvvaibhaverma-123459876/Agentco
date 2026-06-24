/**
 * Governance & safety routes (extended)
 * ====================================
 * Integrates governance-rbac, invariant-validator, safety and provenance into the
 * deployable app. All were orphaned (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { governanceRBACService } from '../services/governance-rbac.service';
import { InvariantValidatorService } from '../services/invariant-validator.service';
import { safetyService } from '../services/safety.service';
import { provenance } from '../services/provenance.service';

const invariantValidator = new InvariantValidatorService();

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function governanceExtRoutes(fastify: FastifyInstance) {
  // RBAC permission check.
  fastify.post('/api/governance/rbac/check', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.entityId !== 'string' || typeof b.permission !== 'string') {
      return reply.status(400).send({ error: 'entityId and permission are required' });
    }
    const allowed = await governanceRBACService.hasPermission(b.entityId, b.permission);
    return reply.send({ entityId: b.entityId, permission: b.permission, allowed });
  });

  // Invariant validation for a claim before persistence (evidence-backed rule).
  fastify.post('/api/governance/invariant/claim', { preHandler: requireScope('claims:register') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.text !== 'string') {
      return reply.status(400).send({ error: 'text is required' });
    }
    const result = await invariantValidator.validateClaimBeforePersist({
      text: b.text,
      support_source_ids: Array.isArray(b.support_source_ids) ? b.support_source_ids.map(String) : [],
      confidence: b.confidence !== undefined ? Number(b.confidence) : undefined,
    });
    return reply.send(result);
  });

  // Build a safety-wrapped response (citations, confidence flags, risk level) and audit it.
  fastify.post('/api/safety/response', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.answer !== 'string') {
      return reply.status(400).send({ error: 'answer is required' });
    }
    const safe = safetyService.createSafeResponse(
      b.answer,
      Number(b.confidence ?? 0),
      Array.isArray(b.sourceFactIds) ? b.sourceFactIds.map(String) : [],
      Array.isArray(b.reasoning) ? b.reasoning.map(String) : undefined,
    );
    const audit = safetyService.auditResponse(safe);
    return reply.send({ response: safe, audit });
  });

  // Verify a detached Ed25519 provenance signature over a payload.
  fastify.post('/api/provenance/verify', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.payload !== 'object' || b.payload === null || typeof b.signatureHex !== 'string') {
      return reply.status(400).send({ error: 'payload (object) and signatureHex (string) are required' });
    }
    const valid = provenance.verifyDetached(b.payload as object, b.signatureHex);
    return reply.send({ valid });
  });
}
