/**
 * Autonomy Dashboard API Routes
 * =============================
 * Read-only endpoints for LEVEL_3 autonomy dashboard.
 * Provides access to runs, tasks, candidates, evals, and observability data.
 */

import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { db } from '../db/client';

function isDashboardSchemaUnavailable(error: any): boolean {
  return (
    error?.code === '42P01' ||
    error?.code === '42703' ||
    /relation ".*" does not exist/i.test(error?.message ?? '') ||
    /column ".*" does not exist/i.test(error?.message ?? '')
  );
}

export async function autonomyDashboardRoutes(fastify: FastifyInstance) {
  /**
   * GET /api/autonomy/runs/:runId
   * Get a specific autonomy run
   */
  fastify.get<{ Params: { runId: string } }>(
    '/api/autonomy/runs/:runId',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { runId } = request.params as { runId: string };

        const result = await db.query(
          `SELECT id, run_id, status, trace_id, current_step, total_steps, task_id,
                  episode_id, trajectory_ids, replay_batch_id, learner_run_id,
                  candidate_id, eval_run_id, scorecard_id, promotion_eligible,
                  error, started_at, completed_at
           FROM autonomy_runs WHERE run_id = $1`,
          [runId]
        );

        if (result.rows.length === 0) {
          return reply.code(404).send({
            status: 'error',
            message: 'Run not found',
          });
        }

        const row = result.rows[0];
        const run = {
          id: row.id,
          runId: row.run_id,
          status: row.status,
          traceId: row.trace_id,
          taskId: row.task_id,
          episodeId: row.episode_id,
          trajectoryIds: row.trajectory_ids || [],
          replayBatchId: row.replay_batch_id,
          learnerRunId: row.learner_run_id,
          candidateId: row.candidate_id,
          evalRunId: row.eval_run_id,
          scorecardId: row.scorecard_id,
          promotionEligible: row.promotion_eligible || false,
          error: row.error,
          startedAt: row.started_at,
          completedAt: row.completed_at,
        };

        reply.code(200).send({
          status: 'success',
          run,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(404).send({ status: 'error', message: 'Run not found' });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/runs?limit=10
   * List recent autonomy runs
   */
  fastify.get<{ Querystring: { limit?: string } }>(
    '/api/autonomy/runs',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { limit = '10' } = request.query as { limit?: string };
        const parsed = parseInt(limit, 10);
        const limitNum = Math.min(isNaN(parsed) ? 10 : parsed, 100);

        const result = await db.query(
          `SELECT id, run_id, status, trace_id, task_id, episode_id,
                  replay_batch_id, learner_run_id, candidate_id, eval_run_id,
                  scorecard_id, promotion_eligible, error, started_at, completed_at
           FROM autonomy_runs
           ORDER BY started_at DESC
           LIMIT $1`,
          [limitNum]
        );

        const runs = result.rows.map((row) => ({
          id: row.id,
          runId: row.run_id,
          status: row.status,
          traceId: row.trace_id,
          taskId: row.task_id,
          episodeId: row.episode_id,
          replayBatchId: row.replay_batch_id,
          learnerRunId: row.learner_run_id,
          candidateId: row.candidate_id,
          evalRunId: row.eval_run_id,
          scorecardId: row.scorecard_id,
          promotionEligible: row.promotion_eligible || false,
          error: row.error,
          startedAt: row.started_at,
          completedAt: row.completed_at,
        }));

        reply.code(200).send({
          status: 'success',
          runs,
          count: runs.length,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(200).send({ status: 'success', runs: [], count: 0 });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/tasks?limit=20
   * List tasks
   */
  fastify.get<{ Querystring: { limit?: string } }>(
    '/api/autonomy/tasks',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { limit = '20' } = request.query as { limit?: string };
        const parsed = parseInt(limit, 10);
        const limitNum = Math.min(isNaN(parsed) ? 20 : parsed, 100);

        const result = await db.query(
          `SELECT id, task_id, goal_id, status, autonomy_level, risk_level,
                  task_type, created_at, updated_at
           FROM autonomy_tasks
           ORDER BY created_at DESC
           LIMIT $1`,
          [limitNum]
        );

        const tasks = result.rows.map((row) => ({
          id: row.id,
          taskId: row.task_id,
          goalId: row.goal_id,
          status: row.status,
          autonomyLevel: row.autonomy_level,
          riskLevel: row.risk_level,
          taskType: row.task_type,
          createdAt: row.created_at,
          updatedAt: row.updated_at,
        }));

        reply.code(200).send({
          status: 'success',
          tasks,
          count: tasks.length,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(200).send({ status: 'success', tasks: [], count: 0 });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/candidates/:candidateId
   * Get a specific learner candidate
   */
  fastify.get<{ Params: { candidateId: string } }>(
    '/api/autonomy/candidates/:candidateId',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { candidateId } = request.params as { candidateId: string };

        const result = await db.query(
          `SELECT id, learner_run_id, candidate_type, artifact_id, artifact_hash,
                  metrics_before_json, metrics_after_json, improvement_percent,
                  status, created_at, evaluated_at, promoted_at
           FROM learner_candidates WHERE id = $1`,
          [candidateId]
        );

        if (result.rows.length === 0) {
          return reply.code(404).send({
            status: 'error',
            message: 'Candidate not found',
          });
        }

        const row = result.rows[0];
        const candidate = {
          id: row.id,
          learnerRunId: row.learner_run_id,
          candidateType: row.candidate_type,
          artifactId: row.artifact_id,
          artifactHash: row.artifact_hash,
          metricsBeforeJson: row.metrics_before_json,
          metricsAfterJson: row.metrics_after_json,
          improvementPercent: row.improvement_percent,
          status: row.status,
          createdAt: row.created_at,
          evaluatedAt: row.evaluated_at,
          promotedAt: row.promoted_at,
        };

        reply.code(200).send({
          status: 'success',
          candidate,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(404).send({ status: 'error', message: 'Candidate not found' });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/candidates?limit=20
   * List learner candidates
   */
  fastify.get<{ Querystring: { limit?: string } }>(
    '/api/autonomy/candidates',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { limit = '20' } = request.query as { limit?: string };
        const parsed = parseInt(limit, 10);
        const limitNum = Math.min(isNaN(parsed) ? 20 : parsed, 100);

        const result = await db.query(
          `SELECT id, learner_run_id, candidate_type, artifact_id, artifact_hash,
                  metrics_before_json, metrics_after_json, improvement_percent,
                  status, created_at, evaluated_at, promoted_at
           FROM learner_candidates
           ORDER BY created_at DESC
           LIMIT $1`,
          [limitNum]
        );

        const candidates = result.rows.map((row) => ({
          id: row.id,
          learnerRunId: row.learner_run_id,
          candidateType: row.candidate_type,
          artifactId: row.artifact_id,
          artifactHash: row.artifact_hash,
          metricsBeforeJson: row.metrics_before_json,
          metricsAfterJson: row.metrics_after_json,
          improvementPercent: row.improvement_percent,
          status: row.status,
          createdAt: row.created_at,
          evaluatedAt: row.evaluated_at,
          promotedAt: row.promoted_at,
        }));

        reply.code(200).send({
          status: 'success',
          candidates,
          count: candidates.length,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(200).send({ status: 'success', candidates: [], count: 0 });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/evals/scorecards/:scorecardId
   * Get a specific eval scorecard
   */
  fastify.get<{ Params: { scorecardId: string } }>(
    '/api/autonomy/evals/scorecards/:scorecardId',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { scorecardId } = request.params as { scorecardId: string };

        const result = await db.query(
          `SELECT id, eval_run_id, autonomy_score, safety_score, calibration_score,
                  planning_score, memory_score, learner_score, regression_score,
                  overall_score, promotion_eligible, reasoning, created_at
           FROM eval_scorecards WHERE id = $1`,
          [scorecardId]
        );

        if (result.rows.length === 0) {
          return reply.code(404).send({
            status: 'error',
            message: 'Scorecard not found',
          });
        }

        const row = result.rows[0];
        const scorecard = {
          id: row.id,
          evalRunId: row.eval_run_id,
          autonomyScore: row.autonomy_score,
          safetyScore: row.safety_score,
          calibrationScore: row.calibration_score,
          planningScore: row.planning_score,
          memoryScore: row.memory_score,
          learnerScore: row.learner_score,
          regressionScore: row.regression_score,
          overallScore: row.overall_score,
          promotionEligible: row.promotion_eligible,
          reasoning: row.reasoning,
          createdAt: row.created_at,
        };

        reply.code(200).send({
          status: 'success',
          scorecard,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(404).send({ status: 'error', message: 'Scorecard not found' });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/evals/scorecards?limit=20
   * List eval scorecards
   */
  fastify.get<{ Querystring: { limit?: string } }>(
    '/api/autonomy/evals/scorecards',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { limit = '20' } = request.query as { limit?: string };
        const parsed = parseInt(limit, 10);
        const limitNum = Math.min(isNaN(parsed) ? 20 : parsed, 100);

        const result = await db.query(
          `SELECT id, eval_run_id, autonomy_score, safety_score, calibration_score,
                  planning_score, memory_score, learner_score, regression_score,
                  overall_score, promotion_eligible, reasoning, created_at
           FROM eval_scorecards
           ORDER BY created_at DESC
           LIMIT $1`,
          [limitNum]
        );

        const scorecards = result.rows.map((row) => ({
          id: row.id,
          evalRunId: row.eval_run_id,
          autonomyScore: row.autonomy_score,
          safetyScore: row.safety_score,
          calibrationScore: row.calibration_score,
          planningScore: row.planning_score,
          memoryScore: row.memory_score,
          learnerScore: row.learner_score,
          regressionScore: row.regression_score,
          overallScore: row.overall_score,
          promotionEligible: row.promotion_eligible,
          reasoning: row.reasoning,
          createdAt: row.created_at,
        }));

        reply.code(200).send({
          status: 'success',
          scorecards,
          count: scorecards.length,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(200).send({ status: 'success', scorecards: [], count: 0 });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/dashboard/overview
   * Get autonomy dashboard overview stats
   */
  fastify.get(
    '/api/autonomy/dashboard/overview',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        // Get run statistics
        const runsResult = await db.query(
          `SELECT COUNT(*) as total_runs,
                  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_runs,
                  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_runs
           FROM autonomy_runs`
        );

        // Get candidate statistics
        const candidatesResult = await db.query(
          `SELECT COUNT(*) as total_candidates,
                  SUM(CASE WHEN status = 'promoted' THEN 1 ELSE 0 END) as promotion_eligible_count,
                  AVG(CASE WHEN status = 'promoted' THEN improvement_percent ELSE NULL END) as avg_promotion_score
           FROM learner_candidates`
        );

        // Get recent runs
        const recentRunsResult = await db.query(
          `SELECT id, run_id, status, promotion_eligible, started_at, completed_at
           FROM autonomy_runs
           ORDER BY started_at DESC
           LIMIT 5`
        );

        const runsRow = runsResult.rows[0];
        const candidatesRow = candidatesResult.rows[0];

        const overview = {
          totalRuns: parseInt(runsRow.total_runs) || 0,
          completedRuns: parseInt(runsRow.completed_runs) || 0,
          failedRuns: parseInt(runsRow.failed_runs) || 0,
          totalCandidates: parseInt(candidatesRow.total_candidates) || 0,
          promotionEligibleCount: parseInt(candidatesRow.promotion_eligible_count) || 0,
          avgPromotionScore: parseFloat(candidatesRow.avg_promotion_score) || 0,
          recentRuns: recentRunsResult.rows.map((row: any) => ({
            id: row.id,
            runId: row.run_id,
            status: row.status,
            promotionEligible: row.promotion_eligible,
            startedAt: row.started_at,
            completedAt: row.completed_at,
          })),
        };

        reply.code(200).send({
          status: 'success',
          overview,
        });
      } catch (error: any) {
        if (isDashboardSchemaUnavailable(error)) {
          return reply.code(200).send({
            status: 'success',
            overview: {
              totalRuns: 0,
              completedRuns: 0,
              failedRuns: 0,
              totalCandidates: 0,
              promotionEligibleCount: 0,
              avgPromotionScore: 0,
              recentRuns: [],
            },
          });
        }
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/audit?run_id=:runId
   * Get audit trail for a run
   */
  fastify.get<{ Querystring: { run_id?: string } }>(
    '/api/autonomy/audit',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { run_id } = request.query as { run_id?: string };

        if (!run_id) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required parameter: run_id',
          });
        }

        const result = await db.query(
          `SELECT id, trace_id, event_type, entity_type, status, timestamp, details
           FROM audit_events
           WHERE trace_id IN (
             SELECT trace_id FROM autonomy_runs WHERE run_id = $1
           )
           ORDER BY timestamp ASC`,
          [run_id]
        );

        const events = result.rows.map((row: any) => ({
          id: row.id,
          traceId: row.trace_id,
          eventType: row.event_type,
          entityType: row.entity_type,
          status: row.status,
          timestamp: row.timestamp,
          details: row.details || {},
        }));

        reply.code(200).send({
          status: 'success',
          events,
          count: events.length,
        });
      } catch (error: any) {
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

  /**
   * GET /api/autonomy/observability/traces?run_id=:runId
   * Get observability traces for a run
   */
  fastify.get<{ Querystring: { run_id?: string } }>(
    '/api/autonomy/observability/traces',
    async (request: FastifyRequest, reply: FastifyReply) => {
      try {
        const { run_id } = request.query as { run_id?: string };

        if (!run_id) {
          return reply.code(400).send({
            status: 'error',
            message: 'Missing required parameter: run_id',
          });
        }

        const result = await db.query(
          `SELECT id, trace_id, span_id, operation, duration, status, timestamp
           FROM observability_traces
           WHERE trace_id IN (
             SELECT trace_id FROM autonomy_runs WHERE run_id = $1
           )
           ORDER BY timestamp ASC`,
          [run_id]
        );

        const traces = result.rows.map((row: any) => ({
          id: row.id,
          traceId: row.trace_id,
          spanId: row.span_id,
          operation: row.operation,
          duration: row.duration,
          status: row.status,
          timestamp: row.timestamp,
        }));

        reply.code(200).send({
          status: 'success',
          traces,
          count: traces.length,
        });
      } catch (error: any) {
        reply.code(500).send({
          status: 'error',
          message: 'Request failed',
        });
      }
    }
  );

}
