import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { learningService } from '../services/learning.service';

/**
 * Learning Middleware: Automatically capture learning signals from operations
 *
 * Usage:
 *   fastify.addHook('preHandler', learningSignalCapture);
 *
 * Captures signals from:
 *   - POST requests (decisions/actions)
 *   - PUT requests (updates/modifications)
 *   - DELETE requests (removals)
 *   - GET requests that return decision-relevant data
 */

interface RequestContext {
  operationType: 'decision' | 'outcome' | 'evidence_update' | 'contradiction' | 'unknown';
  agentId?: string;
  resourceId?: string;
  action?: string;
}

/**
 * Analyze request to determine signal type
 */
function analyzeRequest(req: FastifyRequest): RequestContext {
  const method = req.method.toUpperCase();
  const path = req.url;
  const body = req.body as Record<string, any>;

  // Extract agent ID from path or body
  const agentIdMatch = path.match(/\/agents\/([^/]+)/);
  const agentId = agentIdMatch ? agentIdMatch[1] : body?.agent_id;

  // Determine operation type
  if (method === 'POST' && path.includes('/dispatch')) {
    return {
      operationType: 'decision',
      agentId,
      action: 'dispatch',
      resourceId: body?.task_id,
    };
  }

  if (method === 'POST' && path.includes('/learning/signal')) {
    return {
      operationType: body?.type || 'decision',
      agentId: body?.agent_id,
      action: 'signal',
    };
  }

  if (method === 'POST' && path.includes('/evidence')) {
    return {
      operationType: 'evidence_update',
      agentId,
      action: 'create_evidence',
    };
  }

  if (method === 'POST' && path.includes('/overrides')) {
    return {
      operationType: 'decision',
      agentId,
      action: 'override_request',
    };
  }

  if (method === 'POST' && path.includes('/audit')) {
    return {
      operationType: 'outcome',
      agentId,
      action: 'audit_log',
    };
  }

  return {
    operationType: 'unknown',
    agentId,
  };
}

/**
 * Capture signal before request is processed
 */
export async function capturePreSignal(request: FastifyRequest, reply: FastifyReply) {
  const context = analyzeRequest(request);

  if (context.operationType !== 'unknown' && context.agentId) {
    const body = request.body as Record<string, any>;

    // Capture pre-request signal (intent)
    learningService.captureSignal(
      context.agentId,
      'decision',
      {
        action: context.action,
        resource_id: context.resourceId,
        method: request.method,
        path: request.url,
        body: JSON.stringify(body).substring(0, 500), // Truncate for brevity
        confidence: 0.7, // Initial confidence in the decision
      },
      `http://${request.method.toLowerCase()}/${context.action}/${Date.now()}`,
    );
  }
}

/**
 * Capture signal after request is processed
 */
export function capturePostSignal(fastify: FastifyInstance) {
  return fastify.addHook('onResponse', async (request: FastifyRequest, reply: FastifyReply) => {
    const context = analyzeRequest(request);

    if (context.operationType !== 'unknown' && context.agentId) {
      const statusCode = reply.statusCode;
      const success = statusCode >= 200 && statusCode < 300;

      // Capture post-request signal (outcome)
      learningService.captureSignal(
        context.agentId,
        'outcome',
        {
          action: context.action,
          resource_id: context.resourceId,
          method: request.method,
          path: request.url,
          status: statusCode,
          success,
          outcome: success ? 'success' : 'failure',
          confidence: success ? 0.9 : 0.6,
        },
        `http://${request.method.toLowerCase()}/${context.action}/outcome/${Date.now()}`,
      );
    }
  });
}

/**
 * Capture contradiction signals from validation errors
 */
export function captureValidationSignal(request: FastifyRequest, error: any) {
  if (error.validation) {
    const body = request.body as Record<string, any>;
    const agentIdMatch = request.url.match(/\/agents\/([^/]+)/);
    const agentId = agentIdMatch ? agentIdMatch[1] : 'unknown';

    learningService.captureSignal(
      agentId,
      'contradiction',
      {
        claim1: JSON.stringify(body),
        claim2: 'schema validation',
        error: error.message,
        independent: true,
        confidence: 0.8,
      },
      `validation://error/${Date.now()}`,
    );
  }
}

/**
 * Register learning middleware on Fastify instance
 */
export async function registerLearningMiddleware(fastify: FastifyInstance) {
  // Capture pre-signal (intent) for key operations
  fastify.addHook('preHandler', capturePreSignal);

  // Capture post-signal (outcome) for all responses
  capturePostSignal(fastify);

  // Also add error handler for contradictions
  fastify.setErrorHandler((error: any, request, reply) => {
    captureValidationSignal(request, error);
    reply.status(400).send({ error: error?.message || 'Unknown error' });
  });
}

/**
 * Utility: Create a learning-aware route wrapper
 *
 * Usage:
 *   const route = withLearning(
 *     async (req: FastifyRequest) => {
 *       // route logic
 *     },
 *     'agent_id_param_name'
 *   );
 */
export function withLearning(
  handler: (req: FastifyRequest, reply: FastifyReply) => Promise<any>,
  agentIdParam: string = 'id',
) {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const params = request.params as Record<string, any>;
    const agentId = params[agentIdParam];

    try {
      // Capture intent
      learningService.captureSignal(
        agentId,
        'decision',
        {
          handler: handler.name,
          params: JSON.stringify(params).substring(0, 500),
          confidence: 0.7,
        },
        `handler://${handler.name}/${Date.now()}`,
      );

      // Execute handler
      const result = await handler(request, reply);

      // Capture outcome
      learningService.captureSignal(
        agentId,
        'outcome',
        {
          handler: handler.name,
          status: 'success',
          result: typeof result === 'string' ? result : 'object',
          confidence: 0.9,
        },
        `handler://${handler.name}/outcome/${Date.now()}`,
      );

      return result;
    } catch (error) {
      // Capture error
      learningService.captureSignal(
        agentId,
        'outcome',
        {
          handler: handler.name,
          status: 'error',
          error: (error as Error).message,
          confidence: 0.8,
        },
        `handler://${handler.name}/error/${Date.now()}`,
      );

      throw error;
    }
  };
}
