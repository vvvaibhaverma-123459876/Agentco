/**
 * Civilization routes
 * ===================
 * Exposes the civilization layer through the deployable HTTP app, integrating it with
 * the autonomous-learning runtime. Before this, the civilization/bridge/orchestrator
 * were reachable from no deployable entrypoint (see CIVILIZATION_AUDIT.md).
 *
 * - POST /api/civilization/solve            → multi-service governed solve
 * - POST /api/civilization/work             → route institutional work into the autonomy loop
 * - POST /api/civilization/work/:id/complete → score completed work back into reputation
 */
import type { FastifyInstance, FastifyRequest } from 'fastify';
import { requireScope } from '../security';
import { civilizationService } from '../services/civilization.service';
import { autonomyCivilizationBridgeService } from '../services/autonomy-civilization-bridge.service';

function bodyOf(req: FastifyRequest): Record<string, unknown> {
  return (req.body ?? {}) as Record<string, unknown>;
}

export async function civilizationRoutes(fastify: FastifyInstance) {
  // Governed multi-service solve through the civilization.
  fastify.post('/api/civilization/solve', async (req, reply) => {
    const { question } = bodyOf(req);
    if (typeof question !== 'string' || !question.trim()) {
      return reply.status(400).send({ error: 'question (non-empty string) is required' });
    }
    try {
      const result = await civilizationService.solveWithCivilization(question);
      return reply.send(result);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return reply.status(502).send({ error: `civilization solve failed: ${message}` });
    }
  });

  // Route an institutional work request into the autonomy loop (drives the bridge).
  fastify.post(
    '/api/civilization/work',
    { preHandler: requireScope('task:dispatch') },
    async (req, reply) => {
      const { work_request_id, objective, specialists } = bodyOf(req);
      if (typeof work_request_id !== 'string' || !work_request_id) {
        return reply.status(400).send({ error: 'work_request_id is required' });
      }
      if (typeof objective !== 'string' || !objective) {
        return reply.status(400).send({ error: 'objective is required' });
      }
      const roles = Array.isArray(specialists) ? specialists.map(String) : [];
      try {
        const autonomyGoalId = await autonomyCivilizationBridgeService.routeWorkToAutonomy(
          work_request_id,
          objective,
          roles,
        );
        return reply.status(202).send({ work_request_id, autonomy_goal_id: autonomyGoalId, status: 'in_progress' });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return reply.status(502).send({ error: `work routing failed: ${message}` });
      }
    },
  );

  // Report completion of routed work; scores it back into reputation.
  fastify.post<{ Params: { id: string } }>(
    '/api/civilization/work/:id/complete',
    { preHandler: requireScope('institutions:mutate') },
    async (req, reply) => {
      const b = bodyOf(req);
      const result = {
        work_request_id: req.params.id,
        specialist_role: String(b.specialist_role ?? ''),
        evidence_count: Number(b.evidence_count ?? 0),
        claim_count: Number(b.claim_count ?? 0),
        confidence_avg: Number(b.confidence_avg ?? 0),
        tokens_used: Number(b.tokens_used ?? 0),
        iterations_used: Number(b.iterations_used ?? 0),
        time_elapsed_seconds: Number(b.time_elapsed_seconds ?? 0),
      };
      if (!result.specialist_role) {
        return reply.status(400).send({ error: 'specialist_role is required' });
      }
      try {
        const score = autonomyCivilizationBridgeService.computePerformanceScore(result);
        await autonomyCivilizationBridgeService.reportWorkCompletion(result);
        return reply.send({ work_request_id: result.work_request_id, score, status: 'completed' });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return reply.status(502).send({ error: `work completion failed: ${message}` });
      }
    },
  );
}
