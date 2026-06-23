import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { deadlockDetectorService } from '../services/deadlock-detector.service';
import { reputationScaleService } from '../services/reputation-scale.service';

export async function phase3HardeningRoutes(
  fastify: FastifyInstance
): Promise<void> {
  /**
   * POST /api/civilization/goals/:goalId/lock
   * Acquire exclusive execution lock on goal
   */
  fastify.post('/api/civilization/goals/:goalId/lock', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { goalId } = req.params as { goalId: string };
      const { institution_id, acquired_by } = req.body as any;

      if (!institution_id || !acquired_by) {
        return reply.status(400).send({
          error: 'institution_id and acquired_by are required',
        });
      }

      const lock = await deadlockDetectorService.acquireGoalLock(
        goalId,
        institution_id,
        acquired_by
      );

      if (!lock) {
        return reply.status(409).send({
          error: 'Goal lock already held by another process',
          goal_id: goalId,
        });
      }

      return reply.status(201).send({
        lock_id: lock.lock_id,
        goal_id: lock.goal_id,
        status: 'acquired',
      });
    } catch (e: any) {
      return reply.status(400).send({ error: e.message });
    }
  });

  /**
   * POST /api/civilization/goals/:goalId/unlock
   * Release execution lock
   */
  fastify.post('/api/civilization/goals/:goalId/unlock', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { lockId } = req.body as any;

      if (!lockId) {
        return reply.status(400).send({ error: 'lockId is required' });
      }

      const released = await deadlockDetectorService.releaseGoalLock(lockId);

      if (!released) {
        return reply.status(400).send({ error: 'Lock not found or already released' });
      }

      return reply.send({ status: 'released', lock_id: lockId });
    } catch (e: any) {
      return reply.status(400).send({ error: e.message });
    }
  });

  /**
   * GET /api/civilization/institutions/:institutionId/deadlock-check
   * Detect circular dependencies
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/deadlock-check',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };

        const result = await deadlockDetectorService.detectCircularDependencies(
          institutionId
        );

        return reply.send({
          institution_id: institutionId,
          has_circular_dependency: result.hasCycle,
          circular_path: result.cycle,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * POST /api/civilization/consistency-check
   * Run consistency verification on institution state
   */
  fastify.post('/api/civilization/consistency-check', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { institution_id, check_type } = req.body as any;

      if (!institution_id || !check_type) {
        return reply.status(400).send({
          error: 'institution_id and check_type are required',
        });
      }

      const result = await deadlockDetectorService.runConsistencyCheck(
        institution_id,
        check_type
      );

      return reply.send({
        institution_id: institution_id,
        check_type: check_type,
        passed: result.checkPassed,
        inconsistencies: result.inconsistencies,
      });
    } catch (e: any) {
      return reply.status(400).send({ error: e.message });
    }
  });

  /**
   * GET /api/civilization/institutions/:institutionId/deadlock-incidents
   * Get recorded deadlock incidents
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/deadlock-incidents',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };

        const incidents = await deadlockDetectorService.getDeadlockIncidents(
          institutionId
        );

        return reply.send({
          institution_id: institutionId,
          incidents: incidents,
          total: incidents.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * GET /api/civilization/institutions/:institutionId/reputation-distribution
   * Get reputation stats across all specialists
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/reputation-distribution',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };

        const distribution = await reputationScaleService.getReputationDistribution(
          institutionId
        );

        return reply.send(distribution);
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * GET /api/civilization/institutions/:institutionId/underperformers
   * Find bottom 10% specialists
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/underperformers',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };
        const { percentile } = req.query as { percentile?: string };

        const underperformers = await reputationScaleService.getUnderperformingSpecialists(
          institutionId,
          percentile ? parseInt(percentile) : 10
        );

        return reply.send({
          institution_id: institutionId,
          underperformers: underperformers,
          total: underperformers.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * GET /api/civilization/institutions/:institutionId/top-performers
   * Find top 10% specialists
   */
  fastify.get(
    '/api/civilization/institutions/:institutionId/top-performers',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };
        const { percentile } = req.query as { percentile?: string };

        const topPerformers = await reputationScaleService.getTopPerformers(
          institutionId,
          percentile ? parseInt(percentile) : 90
        );

        return reply.send({
          institution_id: institutionId,
          top_performers: topPerformers,
          total: topPerformers.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * GET /api/civilization/reputation-anomalies/:institutionId
   * Detect reputation anomalies
   */
  fastify.get(
    '/api/civilization/reputation-anomalies/:institutionId',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { institutionId } = req.params as { institutionId: string };

        const anomalies = await reputationScaleService.detectReputationAnomalies(
          institutionId
        );

        return reply.send({
          institution_id: institutionId,
          anomalies: anomalies,
          total: anomalies.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * GET /api/civilization/reputation-trend/:entityId
   * Get reputation trend over time
   */
  fastify.get(
    '/api/civilization/reputation-trend/:entityId',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { entityId } = req.params as { entityId: string };
        const { entity_type, window_days } = req.query as {
          entity_type?: string;
          window_days?: string;
        };

        if (!entity_type) {
          return reply.status(400).send({ error: 'entity_type query param required' });
        }

        const trend = await reputationScaleService.getReputationTrend(
          entityId,
          entity_type,
          window_days ? parseInt(window_days) : 30
        );

        return reply.send({
          entity_id: entityId,
          entity_type: entity_type,
          trend: trend,
          data_points: trend.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );

  /**
   * POST /api/civilization/batch-update-reputations
   * Batch update multiple specialist reputations
   */
  fastify.post(
    '/api/civilization/batch-update-reputations',
    async (req: FastifyRequest, reply: FastifyReply) => {
      try {
        const { updates } = req.body as any;

        if (!Array.isArray(updates) || updates.length === 0) {
          return reply.status(400).send({
            error: 'updates must be non-empty array',
          });
        }

        const result = await reputationScaleService.batchUpdateReputations(
          updates
        );

        return reply.send({
          status: 'completed',
          updated: result.updated,
          failed: result.failed,
          total: updates.length,
        });
      } catch (e: any) {
        return reply.status(400).send({ error: e.message });
      }
    }
  );
}
