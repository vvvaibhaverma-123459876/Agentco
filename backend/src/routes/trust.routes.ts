/**
 * Trust + reputation routes
 * =========================
 * Integrates the trust cluster (trustworthiness, trust-scoring, trust-impact-assessment,
 * reputation-scale) into the deployable app. All were orphaned (see CIVILIZATION_AUDIT.md).
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { trustworthinessService } from '../services/trustworthiness.service';
import { trustScoringService } from '../services/trust-scoring.service';
import { trustImpactAssessmentService } from '../services/trust-impact-assessment.service';
import { reputationScaleService } from '../services/reputation-scale.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}
function num(v: unknown, d = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

export async function trustRoutes(fastify: FastifyInstance) {
  // 6-dimension trustworthiness score (pure).
  fastify.post('/api/trust/score', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const score = trustworthinessService.computeTrustScore(
      num(b.accuracy), num(b.calibrationError), num(b.consistency),
      num(b.explainability), num(b.uncertaintyQuality), num(b.conformalCoverage),
    );
    return reply.send(score);
  });

  // Domain-aware answer risk gate (pure).
  fastify.post('/api/trust/assess-risk', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const domain = (['safety', 'financial', 'medical', 'general'].includes(String(b.domain))
      ? String(b.domain) : 'general') as 'safety' | 'financial' | 'medical' | 'general';
    const result = trustworthinessService.assessAnswerRisk(String(b.answer ?? ''), num(b.trustScore), domain);
    return reply.send(result);
  });

  // Dimensional trust score from benchmark-style inputs (pure).
  fastify.post('/api/trust/dimensional', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const b = bodyOf(req);
    const score = trustScoringService.computeTrustScore(
      num(b.accuracy), num(b.calibrationGap), num(b.domainConsistency),
      num(b.citedSourceCount), num(b.confidenceIntervalQuality), num(b.domainCoverage),
    );
    return reply.send(score);
  });

  // Policy trust-impact recommendation (DB-backed).
  fastify.post('/api/trust/impact/:policyId/recommendation', { preHandler: requireScope('governance:mutate') }, async (req, reply) => {
    const b = bodyOf(req) as { metrics?: Parameters<typeof trustImpactAssessmentService.produceRecommendation>[0] };
    if (!b.metrics) return reply.status(400).send({ error: 'metrics object is required' });
    const recommendation = await trustImpactAssessmentService.produceRecommendation(b.metrics);
    return reply.send({ recommendation });
  });

  // Reputation distribution for an institution (DB-backed).
  fastify.get<{ Params: { id: string } }>('/api/institutions/:id/reputation', { preHandler: requireScope('trust:read') }, async (req, reply) => {
    const distribution = await reputationScaleService.getReputationDistribution(req.params.id);
    return reply.send(distribution);
  });
}
