import { FastifyInstance } from 'fastify';
import { planner } from '../services/planner.service';
import { rewardCalculator } from '../services/reward-calculator.service';
import { evalHarness } from '../services/eval-harness.service';

/**
 * PHASES 6-8: Planning, Rewards, and Evaluation API Routes
 */

export async function phases6_8Routes(fastify: FastifyInstance) {
  // ============================================================
  // PHASE 6: Planning Routes
  // ============================================================

  /**
   * POST /api/plans - Create a new plan from a goal
   */
  fastify.post<{ Body: any }>('/api/plans', async (request, reply) => {
    try {
      const { goalId, plannerAgentId, horizon, traceId, runId } = request.body;

      if (!goalId) {
        return reply.code(400).send({ status: 'error', error: 'goalId required' });
      }

      const result = await planner.createPlan({
        goalId,
        plannerAgentId,
        horizon,
        traceId,
        runId,
      });

      reply.code(201).send({
        status: 'success',
        planId: result.planId,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/plans/:planId/generate - Generate plan from goal
   */
  fastify.post<{ Params: { planId: string } }>('/api/plans/:planId/generate', async (request, reply) => {
    try {
      const { goalId } = request.body;

      if (!goalId) {
        return reply.code(400).send({ status: 'error', error: 'goalId required' });
      }

      const result = await planner.generatePlanFromGoal(goalId);

      reply.code(201).send({
        status: 'success',
        ...result,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * GET /api/plans/:planId - Get plan details
   */
  fastify.get<{ Params: { planId: string } }>('/api/plans/:planId', async (request, reply) => {
    try {
      const plan = await planner.getPlan(request.params.planId);

      if (!plan) {
        return reply.code(404).send({ status: 'error', error: 'Plan not found' });
      }

      reply.code(200).send({
        status: 'success',
        plan,
      });
    } catch (error: any) {
      reply.code(500).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/plans/:planId/validate - Validate plan DAG
   */
  fastify.post<{ Params: { planId: string } }>('/api/plans/:planId/validate', async (request, reply) => {
    try {
      const validation = await planner.validatePlan(request.params.planId);

      reply.code(200).send({
        status: 'success',
        ...validation,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/plans/:planId/approve - Approve a plan
   */
  fastify.post<{ Params: { planId: string }; Body: any }>('/api/plans/:planId/approve', async (
    request,
    reply
  ) => {
    try {
      const { reviewerId } = request.body;

      if (!reviewerId) {
        return reply.code(400).send({ status: 'error', error: 'reviewerId required' });
      }

      await planner.approvePlan(request.params.planId, reviewerId);

      const plan = await planner.getPlan(request.params.planId);

      reply.code(200).send({
        status: 'success',
        plan,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/plans/:planId/activate - Activate a plan
   */
  fastify.post<{ Params: { planId: string } }>('/api/plans/:planId/activate', async (request, reply) => {
    try {
      await planner.activatePlan(request.params.planId);

      const plan = await planner.getPlan(request.params.planId);

      reply.code(200).send({
        status: 'success',
        plan,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * GET /api/plans - List plans
   */
  fastify.get<{ Querystring: any }>('/api/plans', async (request, reply) => {
    try {
      const plans = await planner.listPlans({
        goalId: request.query.goalId,
        status: request.query.status,
        riskLevel: request.query.riskLevel,
      });

      reply.code(200).send({
        status: 'success',
        plans,
        count: plans.length,
      });
    } catch (error: any) {
      reply.code(500).send({ status: 'error', error: error.message });
    }
  });

  // ============================================================
  // PHASE 7: Reward & Outcome Routes
  // ============================================================

  /**
   * POST /api/outcomes - Create an outcome
   */
  fastify.post<{ Body: any }>('/api/outcomes', async (request, reply) => {
    try {
      const { goalId, planId, outcomeType, objectiveResult, traceId } = request.body;

      if (!outcomeType) {
        return reply.code(400).send({ status: 'error', error: 'outcomeType required' });
      }

      const result = await rewardCalculator.createOutcome({
        goalId,
        planId,
        outcomeType,
        objectiveResult,
        traceId,
      });

      reply.code(201).send({
        status: 'success',
        outcomeId: result.outcomeId,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/reward-functions - Register reward function
   */
  fastify.post<{ Body: any }>('/api/reward-functions', async (request, reply) => {
    try {
      const { name, domain, version, formula, owner, riskLevel } = request.body;

      if (!name || !domain || !version || !formula) {
        return reply.code(400).send({ status: 'error', error: 'Missing required fields' });
      }

      const result = await rewardCalculator.registerRewardFunction({
        name,
        domain,
        version,
        formula,
        owner,
        riskLevel,
      });

      reply.code(201).send({
        status: 'success',
        functionId: result.functionId,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/outcomes/:outcomeId/calculate-reward - Calculate reward
   */
  fastify.post<{ Params: { outcomeId: string }; Body: any }>('/api/outcomes/:outcomeId/calculate-reward', async (
    request,
    reply
  ) => {
    try {
      const { rewardFunctionId, traceId } = request.body;

      if (!rewardFunctionId) {
        return reply.code(400).send({ status: 'error', error: 'rewardFunctionId required' });
      }

      const result = await rewardCalculator.calculateReward(
        request.params.outcomeId,
        rewardFunctionId,
        traceId
      );

      reply.code(200).send({
        status: 'success',
        ...result,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * GET /api/reward-functions - List reward functions
   */
  fastify.get<{ Querystring: any }>('/api/reward-functions', async (request, reply) => {
    try {
      const functions = await rewardCalculator.listRewardFunctions({
        domain: request.query.domain,
        active: request.query.active === 'true',
      });

      reply.code(200).send({
        status: 'success',
        functions,
        count: functions.length,
      });
    } catch (error: any) {
      reply.code(500).send({ status: 'error', error: error.message });
    }
  });

  // ============================================================
  // PHASE 8: Evaluation Harness Routes
  // ============================================================

  /**
   * POST /api/eval/run - Run evaluation
   */
  fastify.post<{ Body: any }>('/api/eval/run', async (request, reply) => {
    try {
      const { suiteId, targetType, targetId, baselineRef, candidateRef, traceId } = request.body;

      if (!suiteId) {
        return reply.code(400).send({ status: 'error', error: 'suiteId required' });
      }

      const result = await evalHarness.runEvaluation({
        suiteId,
        targetType,
        targetId,
        baselineRef,
        candidateRef,
        traceId,
      });

      reply.code(201).send({
        status: 'success',
        ...result,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });

  /**
   * GET /api/eval/runs - List eval runs
   */
  fastify.get<{ Querystring: any }>('/api/eval/runs', async (request, reply) => {
    try {
      const runs = await evalHarness.listEvalRuns({
        suiteId: request.query.suiteId,
        status: request.query.status,
        promotionEligible: request.query.promotionEligible === 'true',
      });

      reply.code(200).send({
        status: 'success',
        runs,
        count: runs.length,
      });
    } catch (error: any) {
      reply.code(500).send({ status: 'error', error: error.message });
    }
  });

  /**
   * GET /api/eval/runs/:evalRunId/scorecard - Get scorecard
   */
  fastify.get<{ Params: { evalRunId: string } }>('/api/eval/runs/:evalRunId/scorecard', async (request, reply) => {
    try {
      const scorecard = await evalHarness.getScorecard(request.params.evalRunId);

      if (!scorecard) {
        return reply.code(404).send({ status: 'error', error: 'Scorecard not found' });
      }

      reply.code(200).send({
        status: 'success',
        scorecard,
      });
    } catch (error: any) {
      reply.code(500).send({ status: 'error', error: error.message });
    }
  });

  /**
   * POST /api/eval/runs/:evalRunId/promote - Promote candidate
   */
  fastify.post<{ Params: { evalRunId: string }; Body: any }>('/api/eval/runs/:evalRunId/promote', async (
    request,
    reply
  ) => {
    try {
      const { targetId, promotionReason } = request.body;

      if (!targetId) {
        return reply.code(400).send({ status: 'error', error: 'targetId required' });
      }

      const result = await evalHarness.promoteCandidate(
        request.params.evalRunId,
        targetId,
        promotionReason || 'Promotion approved'
      );

      reply.code(200).send({
        status: 'success',
        promoted: result.success,
      });
    } catch (error: any) {
      reply.code(400).send({ status: 'error', error: error.message });
    }
  });
}
