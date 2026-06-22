import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { taskEngine, TaskCreationInput } from '../services/task-engine.service';
import { trajectoryStore } from '../services/trajectory-store.service';
import { observability } from '../services/observability.service';

export async function autonomyTaskRoutes(fastify: FastifyInstance) {
  /**
   * POST /api/autonomy/tasks - Create new task
   */
  fastify.post<{ Body: TaskCreationInput }>('/api/autonomy/tasks', async (request, reply) => {
    try {
      const input: TaskCreationInput = {
        ...request.body,
        createdBy: request.body.createdBy || 'system',
      };

      const task = await taskEngine.createTask(input);

      // Record creation in observability
      if (task.traceId) {
        await observability.auditEvent(
          task.traceId,
          'task_created',
          'system',
          input.createdBy,
          'autonomy_task',
          task.id,
          'create',
          undefined,
          'info'
        );
      }

      reply.code(201).send({
        status: 'success',
        task,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * GET /api/autonomy/tasks/:taskId - Get task
   */
  fastify.get<{ Params: { taskId: string } }>('/api/autonomy/tasks/:taskId', async (request, reply) => {
    try {
      const task = await taskEngine.getTask(request.params.taskId);

      if (!task) {
        reply.code(404).send({
          status: 'error',
          error: 'Task not found',
        });
        return;
      }

      reply.code(200).send({
        status: 'success',
        task,
      });
    } catch (error: any) {
      reply.code(500).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/queue - Queue task
   */
  fastify.post<{ Params: { taskId: string } }>('/api/autonomy/tasks/:taskId/queue', async (request, reply) => {
    try {
      await taskEngine.queueTask(request.params.taskId);

      reply.code(200).send({
        status: 'success',
        message: 'Task queued',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/lease - Acquire lease
   */
  fastify.post<{
    Params: { taskId: string };
    Body: { workerId: string; leaseDurationSeconds?: number };
  }>('/api/autonomy/tasks/:taskId/lease', async (request, reply) => {
    try {
      const leaseId = await taskEngine.leaseTask(
        request.params.taskId,
        request.body.workerId,
        request.body.leaseDurationSeconds || 300
      );

      reply.code(200).send({
        status: 'success',
        leaseId,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/start - Start executing
   */
  fastify.post<{ Params: { taskId: string } }>('/api/autonomy/tasks/:taskId/start', async (request, reply) => {
    try {
      await taskEngine.startTask(request.params.taskId);

      reply.code(200).send({
        status: 'success',
        message: 'Task started',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/complete - Complete task
   */
  fastify.post<{
    Params: { taskId: string };
    Body: { result?: Record<string, any> };
  }>('/api/autonomy/tasks/:taskId/complete', async (request, reply) => {
    try {
      await taskEngine.completeTask(request.params.taskId, request.body.result);

      reply.code(200).send({
        status: 'success',
        message: 'Task completed',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/fail - Mark as failed
   */
  fastify.post<{
    Params: { taskId: string };
    Body: { error: string; errorStack?: string; shouldRetry?: boolean };
  }>('/api/autonomy/tasks/:taskId/fail', async (request, reply) => {
    try {
      await taskEngine.failTask(
        request.params.taskId,
        request.body.error,
        request.body.errorStack,
        request.body.shouldRetry ?? true
      );

      reply.code(200).send({
        status: 'success',
        message: 'Task marked as failed',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/cancel - Cancel task
   */
  fastify.post<{
    Params: { taskId: string };
    Body: { reason?: string };
  }>('/api/autonomy/tasks/:taskId/cancel', async (request, reply) => {
    try {
      await taskEngine.cancelTask(request.params.taskId, request.body.reason);

      reply.code(200).send({
        status: 'success',
        message: 'Task cancelled',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * POST /api/autonomy/tasks/:taskId/checkpoint - Save checkpoint
   */
  fastify.post<{
    Params: { taskId: string };
    Body: { stepName: string; stepIndex: number; state: Record<string, any> };
  }>('/api/autonomy/tasks/:taskId/checkpoint', async (request, reply) => {
    try {
      await taskEngine.saveCheckpoint(
        request.params.taskId,
        request.body.stepName,
        request.body.stepIndex,
        request.body.state
      );

      reply.code(200).send({
        status: 'success',
        message: 'Checkpoint saved',
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });

  /**
   * GET /api/autonomy/tasks/:taskId/checkpoint/:stepIndex - Load checkpoint
   */
  fastify.get<{
    Params: { taskId: string; stepIndex: string };
  }>('/api/autonomy/tasks/:taskId/checkpoint/:stepIndex', async (request, reply) => {
    try {
      const state = await taskEngine.loadCheckpoint(
        request.params.taskId,
        parseInt(request.params.stepIndex)
      );

      if (!state) {
        reply.code(404).send({
          status: 'error',
          error: 'Checkpoint not found',
        });
        return;
      }

      reply.code(200).send({
        status: 'success',
        state,
      });
    } catch (error: any) {
      reply.code(400).send({
        status: 'error',
        error: error.message,
      });
    }
  });
}
