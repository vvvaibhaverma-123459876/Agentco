import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { autonomyOrchestrator } from '../services/autonomy-orchestrator.service';

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

      // Execute the real orchestrated loop
      const autonomyRun = await autonomyOrchestrator.executeControlledAutonomyLoop();

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
        error: error.message,
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
          error: error.message,
        });
      }
    }
  );
}
