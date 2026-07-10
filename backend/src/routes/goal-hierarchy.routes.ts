import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { goalHierarchyService } from '../services/goal-hierarchy.service';

export async function goalHierarchyRoutes(
  fastify: FastifyInstance
): Promise<void> {
  /**
   * POST /api/autonomy/institutions/:institutionId/root-goal
   * Create root goal for institution (depth 0)
   */
  fastify.post('/api/autonomy/institutions/:institutionId/root-goal', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { institutionId } = req.params as { institutionId: string };
      const { objective } = req.body as { objective: string };

      if (!objective) {
        return reply.status(400).send({ error: 'objective is required' });
      }

      const rootGoal = await goalHierarchyService.createRootGoal(institutionId, objective);

      return reply.status(201).send(rootGoal);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/goals/:parentGoalId/sub-goals
   * Create sub-goal under parent goal (depth 1)
   */
  fastify.post('/api/autonomy/goals/:parentGoalId/sub-goals', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { parentGoalId } = req.params as { parentGoalId: string };
      const { objective } = req.body as { objective: string };

      if (!objective) {
        return reply.status(400).send({ error: 'objective is required' });
      }

      const subGoal = await goalHierarchyService.createSubGoal(parentGoalId, objective);

      return reply.status(201).send(subGoal);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/goals/:parentSubGoalId/tasks
   * Create task goal under sub-goal (depth 2)
   */
  fastify.post('/api/autonomy/goals/:parentSubGoalId/tasks', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { parentSubGoalId } = req.params as { parentSubGoalId: string };
      const { objective } = req.body as { objective: string };

      if (!objective) {
        return reply.status(400).send({ error: 'objective is required' });
      }

      const taskGoal = await goalHierarchyService.createTaskGoal(parentSubGoalId, objective);

      return reply.status(201).send(taskGoal);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * GET /api/autonomy/institutions/:institutionId/goal-hierarchy
   * Get full goal hierarchy for institution
   */
  fastify.get('/api/autonomy/institutions/:institutionId/goal-hierarchy', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { institutionId } = req.params as { institutionId: string };

      const hierarchy = await goalHierarchyService.getGoalHierarchy(institutionId);

      return reply.send(hierarchy);
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/goals/:parentGoalId/rollup
   * Rollup results from completed child goals to parent
   */
  fastify.post('/api/autonomy/goals/:parentGoalId/rollup', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { parentGoalId } = req.params as { parentGoalId: string };

      const rollupResult = await goalHierarchyService.rollupGoalResults(parentGoalId);

      return reply.send({
        parent_goal_id: parentGoalId,
        rollup_results: rollupResult,
        status: 'rolled_up',
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/evidence/:sourceEvidenceId/deduplicate
   * Mark evidence as duplicate of canonical evidence
   */
  fastify.post('/api/autonomy/evidence/:sourceEvidenceId/deduplicate', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { sourceEvidenceId } = req.params as { sourceEvidenceId: string };
      const { canonical_evidence_id, institution_ids, work_request_ids, confidence } = req.body as any;

      if (!canonical_evidence_id) {
        return reply.status(400).send({ error: 'canonical_evidence_id is required' });
      }

      const dedupId = await goalHierarchyService.deduplicateEvidence(
        sourceEvidenceId,
        canonical_evidence_id,
        institution_ids || [],
        work_request_ids || [],
        confidence || 0.8
      );

      return reply.status(201).send({
        id: dedupId,
        source_evidence_id: sourceEvidenceId,
        canonical_evidence_id: canonical_evidence_id,
        status: 'deduplicated',
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/evidence/:evidenceId/share
   * Share evidence across institutions
   */
  fastify.post('/api/autonomy/evidence/:evidenceId/share', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { evidenceId } = req.params as { evidenceId: string };
      const { source_institution_id, requesting_institution_id, agreement_type } = req.body as any;

      if (!source_institution_id || !requesting_institution_id) {
        return reply.status(400).send({
          error: 'source_institution_id and requesting_institution_id are required',
        });
      }

      const result = await goalHierarchyService.shareEvidenceWithInstitution(
        evidenceId,
        source_institution_id,
        requesting_institution_id,
        agreement_type || 'collaboration'
      );

      return reply.status(201).send({
        id: result.id,
        evidence_id: evidenceId,
        status: result.status,
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * GET /api/autonomy/specialist-teams/patterns
   * Get successful specialist team patterns for adaptation
   */
  fastify.get('/api/autonomy/specialist-teams/patterns', async (
    _req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const patterns = await goalHierarchyService.getSuccessfulTeamPatterns();

      return reply.send({
        patterns: patterns,
        total: patterns.length,
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/specialist-teams/record-pattern
   * Record successful specialist team pattern
   */
  fastify.post('/api/autonomy/specialist-teams/record-pattern', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { team_composition, performance } = req.body as any;

      if (!Array.isArray(team_composition) || team_composition.length === 0) {
        return reply.status(400).send({ error: 'team_composition must be non-empty array' });
      }

      if (typeof performance !== 'number' || performance < 0 || performance > 1) {
        return reply.status(400).send({ error: 'performance must be between 0 and 1' });
      }

      await goalHierarchyService.recordTeamPattern(team_composition, performance);

      return reply.status(201).send({
        status: 'pattern_recorded',
        team_composition: team_composition,
        performance: performance,
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });

  /**
   * POST /api/autonomy/allocation/record-decision
   * Record specialist allocation decision for learning
   */
  fastify.post('/api/autonomy/allocation/record-decision', async (
    req: FastifyRequest,
    reply: FastifyReply
  ) => {
    try {
      const { work_request_id, department_id, specialist_role, allocated_reputation, reasoning } = req.body as any;

      if (!work_request_id || !department_id || !specialist_role) {
        return reply.status(400).send({
          error: 'work_request_id, department_id, and specialist_role are required',
        });
      }

      await goalHierarchyService.recordAllocationDecision(
        work_request_id,
        department_id,
        specialist_role,
        allocated_reputation || 0.5,
        reasoning || ''
      );

      return reply.status(201).send({
        status: 'allocation_recorded',
        work_request_id: work_request_id,
      });
    } catch (e: any) {
      return reply.status(400).send({ error: 'Invalid request' });
    }
  });
}
