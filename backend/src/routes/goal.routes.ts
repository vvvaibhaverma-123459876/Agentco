import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { goalManager } from '../services/goal-manager.service';

/**
 * Goal Management API Routes
 *
 * All routes enforce real logic - no static responses.
 */

export async function goalRoutes(fastify: FastifyInstance) {
  /**
   * GET /api/goals - List goals with filters
   */
  fastify.get<{
    Querystring: {status?: string; domain?: string; riskLevel?: string; agentId?: string};
  }>('/api/goals', async (request, reply) => {
    try {
      const goals = await goalManager.listGoals({
        status: request.query.status,
        domain: request.query.domain,
        riskLevel: request.query.riskLevel,
        agentId: request.query.agentId,
      });

      reply.code(200).send({
        status: 'success',
        goals,
        count: goals.length,
      });
    } catch (error: any) {
      reply.code(500).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals - Propose new goal
   */
  fastify.post<{Body: any}>('/api/goals', async (request, reply) => {
    try {
      const {title, description, source, proposedBy, owningAgentId, owningInstitutionId, domain, expectedValue, riskLevel, autonomyLevelAllowed, successCriteria, stopConditions, traceId, runId} = request.body;

      // Validation
      if (!title || !domain || !proposedBy || !riskLevel || !autonomyLevelAllowed || !successCriteria || !stopConditions) {
        reply.code(400).send({
          status: 'error',
          error: 'Missing required fields: title, domain, proposedBy, riskLevel, autonomyLevelAllowed, successCriteria, stopConditions',
        });
        return;
      }

      const result = await goalManager.proposeGoal({
        title,
        description,
        source: source || 'agent_proposed',
        proposedBy,
        owningAgentId,
        owningInstitutionId,
        domain,
        expectedValue,
        riskLevel,
        autonomyLevelAllowed,
        successCriteria,
        stopConditions,
        traceId,
        runId,
      });

      const goal = await goalManager.getGoal(result.goalId);

      reply.code(201).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * GET /api/goals/:goalId - Get goal details
   */
  fastify.get<{Params: {goalId: string}}>('/api/goals/:goalId', async (request, reply) => {
    try {
      const goal = await goalManager.getGoal(request.params.goalId);

      if (!goal) {
        reply.code(404).send({
          status: 'error',
          error: 'Goal not found',
        });
        return;
      }

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(500).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/evidence - Attach evidence
   */
  fastify.post<{Params: {goalId: string}; Body: any}>('/api/goals/:goalId/evidence', async (request, reply) => {
    try {
      const {evidenceType, evidenceRef, relevanceScore, provenanceJson} = request.body;

      if (!evidenceType || !evidenceRef) {
        reply.code(400).send({
          status: 'error',
          error: 'Missing required fields: evidenceType, evidenceRef',
        });
        return;
      }

      const evidenceId = await goalManager.attachEvidence(
        request.params.goalId,
        evidenceType,
        evidenceRef,
        relevanceScore || 0.8,
        provenanceJson
      );

      reply.code(201).send({
        status: 'success',
        evidenceId,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/budget - Set budget
   */
  fastify.post<{Params: {goalId: string}; Body: any}>('/api/goals/:goalId/budget', async (request, reply) => {
    try {
      const {computeBudget, tokenBudget, timeBudgetSeconds, toolBudget, spendLimit} = request.body;

      const budgetId = await goalManager.setBudget(request.params.goalId, {
        computeBudget,
        tokenBudget,
        timeBudgetSeconds,
        toolBudget,
        spendLimit,
      });

      reply.code(201).send({
        status: 'success',
        budgetId,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/review - Review goal
   */
  fastify.post<{Params: {goalId: string}; Body: any}>('/api/goals/:goalId/review', async (request, reply) => {
    try {
      const {reviewerId, reviewerRole, decision, reason} = request.body;

      if (!reviewerId || !reviewerRole || !decision) {
        reply.code(400).send({
          status: 'error',
          error: 'Missing required fields: reviewerId, reviewerRole, decision',
        });
        return;
      }

      await goalManager.reviewGoal(request.params.goalId, {
        reviewerId,
        reviewerRole,
        decision,
        reason,
      });

      const goal = await goalManager.getGoal(request.params.goalId);

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/activate - Activate goal
   */
  fastify.post<{Params: {goalId: string}}>('/api/goals/:goalId/activate', async (request, reply) => {
    try {
      await goalManager.activateGoal(request.params.goalId);

      const goal = await goalManager.getGoal(request.params.goalId);

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/pause - Pause goal
   */
  fastify.post<{Params: {goalId: string}; Body: {reason?: string}}>('/api/goals/:goalId/pause', async (request, reply) => {
    try {
      await goalManager.pauseGoal(request.params.goalId, request.body.reason);

      const goal = await goalManager.getGoal(request.params.goalId);

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/complete - Complete goal
   */
  fastify.post<{Params: {goalId: string}; Body: {outcomeRef: string}}>('/api/goals/:goalId/complete', async (request, reply) => {
    try {
      const {outcomeRef} = request.body;

      if (!outcomeRef) {
        reply.code(400).send({
          status: 'error',
          error: 'Missing required field: outcomeRef',
        });
        return;
      }

      await goalManager.completeGoal(request.params.goalId, outcomeRef);

      const goal = await goalManager.getGoal(request.params.goalId);

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/goals/:goalId/retire - Retire goal
   */
  fastify.post<{Params: {goalId: string}; Body: {reason?: string}}>('/api/goals/:goalId/retire', async (request, reply) => {
    try {
      await goalManager.retireGoal(request.params.goalId, request.body.reason);

      const goal = await goalManager.getGoal(request.params.goalId);

      reply.code(200).send({
        status: 'success',
        goal,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });
}
