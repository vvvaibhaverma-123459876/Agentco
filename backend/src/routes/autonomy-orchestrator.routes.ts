import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { autonomyOrchestrator } from '../services/autonomy-orchestrator.service';
import { db } from '../db/client';

export async function autonomyOrchestratorRoutes(fastify: FastifyInstance) {
  /**
   * POST /api/autonomy/run-level3-smoke
   *
   * Trigger a complete LEVEL_3 controlled autonomy loop.
   * This executes the full 30-step loop:
   * perception → goal → task → plan → execution → memory → trajectory → outcome →
   * reward → replay → learner → candidate → eval → promotion → canary/rollback
   *
   * Returns the autonomy run with all IDs and status.
   */
  fastify.post('/api/autonomy/run-level3-smoke', async (request: FastifyRequest, reply: FastifyReply) => {
    try {
      console.log('[LEVEL_3] Starting controlled autonomy loop...');

      // Extract optional idempotency_key from request body
      const body = request.body as { idempotency_key?: string } | undefined;
      const idempotencyKey = body?.idempotency_key;

      if (idempotencyKey) {
        console.log(`[LEVEL_3] Using idempotency_key: ${idempotencyKey}`);
      }

      // Execute the real orchestrated loop
      const autonomyRun = await autonomyOrchestrator.executeControlledAutonomyLoop(idempotencyKey);

      console.log('[LEVEL_3] Loop completed successfully');

      reply.code(200).send({
        status: 'success',
        message: 'LEVEL_3 autonomy loop completed',
        run: autonomyRun,
      });
    } catch (error: any) {
      console.error('[LEVEL_3] Loop failed:', error);

      reply.code(500).send({
        status: 'error',
        message: 'LEVEL_3 autonomy loop failed',
        error: 'Request failed',
        stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
      });
    }
  });

  /**
   * GET /api/autonomy/run-level3-smoke/:runId
   *
   * Get details of a completed autonomy run.
   */
  fastify.get<{ Params: { runId: string } }>(
    '/api/autonomy/run-level3-smoke/:runId',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const params = request.params as { runId: string };
        const { runId } = params;

        const run = await autonomyOrchestrator.getRunDetails(runId);

        reply.code(200).send({
          status: 'success',
          run,
        });
      } catch (error: any) {
        reply.code(400).send({
          status: 'error',
          error: 'Request failed',
        });
      }
    }
  );

  /**
   * POST /api/autonomy/action-loop
   *
   * Execute a true end-to-end autonomy action loop with decision-execution cycle.
   * Implements: goal creation → plan → execute → observe → evidence → claims → loop-detect
   * Enforces evidence requirements for claims and detects infinite loops.
   *
   * Body: { goal: string, maxIterations?: number, idempotencyKey?: string }
   * Returns: { goalId, claimsGenerated, actionsExecuted, status, reason }
   */
  fastify.post<{ Body: { goal?: string; maxIterations?: number; idempotencyKey?: string } }>(
    '/api/autonomy/action-loop',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const body = (request.body as { goal?: string; maxIterations?: number; idempotencyKey?: string }) || {};
        const { goal, maxIterations = 10 } = body;

        if (!goal) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required field: goal',
          });
        }

        // Input validation
        if (typeof goal !== 'string' || goal.length === 0) {
          return reply.code(400).send({
            status: 'error',
            message: 'Goal must be a non-empty string',
          });
        }

        if (goal.length > 10000) {
          return reply.code(400).send({
            status: 'error',
            message: 'Goal exceeds maximum length of 10000 characters',
          });
        }

        if (typeof maxIterations !== 'number' || maxIterations <= 0 || maxIterations > 1000) {
          return reply.code(400).send({
            status: 'error',
            message: 'maxIterations must be between 1 and 1000',
          });
        }

        console.log('[ACTION_LOOP] Starting action loop with goal:', goal);

        const result = await autonomyOrchestrator.executeAutonomyActionLoop(
          goal,
          maxIterations,
          body.idempotencyKey
        );

        reply.code(200).send({
          apiStatus: 'success',
          message: 'Autonomy action loop completed',
          ...result,
        });
      } catch (error: any) {
        console.error('[ACTION_LOOP] Failed:', error);

        reply.code(500).send({
          status: 'error',
          message: 'Autonomy action loop failed',
          error: 'Request failed',
          stack: process.env.NODE_ENV === 'development' ? error.stack : undefined,
        });
      }
    }
  );

  /**
   * GET /api/autonomy/actions?goalId=:goalId
   *
   * Get all actions executed for a goal
   */
  fastify.get<{ Querystring: { goalId?: string } }>(
    '/api/autonomy/actions',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { goalId } = (request.query as { goalId?: string });

        if (!goalId) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required parameter: goalId',
          });
        }

        const result = await db.query(
          `SELECT id, action_id, action_type, objective, args, status, started_at,
                  completed_at, observations, created_artifacts, errors
           FROM autonomy_actions
           WHERE goal_id = $1
           ORDER BY decided_at ASC`,
          [goalId]
        );

        const actions = result.rows.map(row => ({
          actionId: row.action_id,
          actionType: row.action_type,
          objective: row.objective,
          args: row.args,
          status: row.status,
          startedAt: row.started_at,
          completedAt: row.completed_at,
          observations: row.observations,
          createdArtifacts: row.created_artifacts,
          errors: row.errors,
        }));

        reply.code(200).send({
          status: 'success',
          actions,
          count: actions.length,
        });
      } catch (error: any) {
        reply.code(500).send({
          status: 'error',
          error: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/evidence?goalId=:goalId
   *
   * Get all evidence collected for a goal
   */
  fastify.get<{ Querystring: { goalId?: string } }>(
    '/api/autonomy/evidence',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { goalId } = (request.query as { goalId?: string });

        if (!goalId) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required parameter: goalId',
          });
        }

        const result = await db.query(
          `SELECT ae.id, ae.source_id, ae.url, ae.title, ae.snippet, ae.retrieved_at,
                  ae.source_type, ae.is_public_access
           FROM autonomy_evidence ae
           JOIN autonomy_actions aa ON ae.action_id = aa.id
           WHERE aa.goal_id = $1
           ORDER BY ae.retrieved_at DESC`,
          [goalId]
        );

        const evidence = result.rows.map(row => ({
          sourceId: row.source_id,
          url: row.url,
          title: row.title,
          snippet: row.snippet,
          retrievedAt: row.retrieved_at,
          sourceType: row.source_type,
          isPublicAccess: row.is_public_access,
        }));

        reply.code(200).send({
          status: 'success',
          evidence,
          count: evidence.length,
        });
      } catch (error: any) {
        reply.code(500).send({
          status: 'error',
          error: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/claims?goalId=:goalId
   *
   * Get all claims generated for a goal
   */
  fastify.get<{ Querystring: { goalId?: string } }>(
    '/api/autonomy/claims',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { goalId } = (request.query as { goalId?: string });

        if (!goalId) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required parameter: goalId',
          });
        }

        const result = await db.query(
          `SELECT ac.id, ac.claim_id, ac.text, ac.status, ac.confidence, ac.support_source_ids,
                  ac.support_snippets, ac.generated_at, ac.generated_by
           FROM autonomy_claims ac
           JOIN autonomy_actions aa ON ac.action_id = aa.id
           WHERE aa.goal_id = $1
           ORDER BY ac.generated_at DESC`,
          [goalId]
        );

        const claims = result.rows.map(row => ({
          claimId: row.claim_id,
          text: row.text,
          status: row.status,
          confidence: row.confidence,
          supportSourceIds: row.support_source_ids,
          supportSnippets: row.support_snippets,
          generatedAt: row.generated_at,
          generatedBy: row.generated_by,
        }));

        reply.code(200).send({
          status: 'success',
          claims,
          count: claims.length,
        });
      } catch (error: any) {
        reply.code(500).send({
          status: 'error',
          error: 'Request failed',
        });
      }
    }
  );
}
