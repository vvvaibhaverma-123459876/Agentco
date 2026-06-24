/**
 * Operations routes
 * =================
 * Integrates the remaining capability services: protected-surface-validator,
 * multi-agent-ensemble, perception, planner, rollback, governance-reputation-integration.
 * All were orphaned (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { isProtected, getProtectedSurfaceDefinitions } from '../services/protected-surface-validator.service';
import { multiAgentEnsembleService } from '../services/multi-agent-ensemble.service';
import { planner } from '../services/planner.service';
import { rollback } from '../services/rollback.service';
import { governanceReputationIntegrationService } from '../services/governance-reputation-integration.service';
import { perception } from '../services/perception.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function operationsRoutes(fastify: FastifyInstance) {
  // Is a given field a protected surface? (pure)
  fastify.get<{ Querystring: { field?: string } }>('/api/protected-surfaces/check', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const field = req.query.field ?? '';
    return reply.send({ field, protected: isProtected(field), definitions: getProtectedSurfaceDefinitions() });
  });

  // Multi-agent expert ensemble status (pure).
  fastify.get('/api/ensemble/experts', { preHandler: requireScope('trust:read') }, async (_req, reply) => {
    return reply.send({ status: multiAgentEnsembleService.getExpertStatus() });
  });

  // Validate a plan DAG for cycles / dangling dependencies.
  fastify.get<{ Params: { id: string } }>('/api/plans/:id/validate', { preHandler: requireScope('task:read') }, async (req, reply) => {
    const result = await planner.validatePlanDAG(req.params.id);
    return reply.send(result);
  });

  // Read a deployment snapshot (rollback safety).
  fastify.get<{ Params: { canaryPlanId: string } }>('/api/rollback/:canaryPlanId/snapshot', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const snapshot = await rollback.getDeploymentSnapshot(req.params.canaryPlanId);
    if (!snapshot) return reply.status(404).send({ error: 'snapshot not found' });
    return reply.send(snapshot);
  });

  // Governance voting weight for an entity (reputation-weighted).
  fastify.get<{ Params: { entityId: string } }>('/api/governance/voting-weight/:entityId', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const weight = await governanceReputationIntegrationService.getVotingWeight(req.params.entityId);
    return reply.send({ entity_id: req.params.entityId, voting_weight: weight });
  });

  // Persist a perception event (dedup-aware ingestion).
  fastify.post('/api/perception/events', { preHandler: requireScope('task:dispatch') }, async (req, reply) => {
    const b = bodyOf(req);
    if (typeof b.sourceId !== 'string' || typeof b.eventType !== 'string' || typeof b.sourceFingerprint !== 'string') {
      return reply.status(400).send({ error: 'sourceId, eventType and sourceFingerprint are required' });
    }
    const result = await perception.persistEvent({
      sourceId: b.sourceId,
      eventType: b.eventType,
      sourceUri: String(b.sourceUri ?? ''),
      sourceFingerprint: b.sourceFingerprint,
      observedAt: b.observedAt ? new Date(String(b.observedAt)) : new Date(),
      payloadJson: (b.payloadJson as Record<string, unknown>) ?? {},
      confidence: Number(b.confidence ?? 0.5),
      provenanceJson: (b.provenanceJson as Record<string, unknown>) ?? {},
    } as Parameters<typeof perception.persistEvent>[0]);
    return reply.status(201).send(result);
  });
}
