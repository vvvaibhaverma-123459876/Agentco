import { FastifyRequest, FastifyReply } from 'fastify';
import { db } from '../db/client';

/**
 * RBAC Middleware
 *
 * Enforces role-based access control on autonomy operations.
 * Different operations require different roles:
 * - READ operations: 'viewer' or higher
 * - CREATE operations: 'task_creator' or higher
 * - PROMOTE operations: 'governor' only
 * - ROLLBACK operations: 'governor' only
 */

export type RBACRole = 'viewer' | 'task_creator' | 'learner_service' | 'eval_service' | 'governor';

const roleHierarchy: Record<RBACRole, number> = {
  viewer: 1,
  task_creator: 2,
  learner_service: 3,
  eval_service: 3,
  governor: 100, // Highest privilege
};

const operationRoles: Record<string, RBACRole[]> = {
  // GET operations - anyone can read
  'GET:/api/autonomy': ['viewer', 'task_creator', 'learner_service', 'eval_service', 'governor'],
  'GET:/api/autonomy/tasks': ['viewer', 'task_creator', 'learner_service', 'eval_service', 'governor'],

  // POST operations - varying requirements
  'POST:/api/autonomy/tasks': ['task_creator', 'governor'],
  'POST:/api/autonomy/run-level3-smoke': ['task_creator', 'governor'],

  // Learner operations - only learner_service or governor
  'POST:/api/autonomy/learner': ['learner_service', 'governor'],

  // Eval operations - only eval_service or governor
  'POST:/api/autonomy/eval': ['eval_service', 'governor'],

  // Critical operations - ONLY governor
  'POST:/api/autonomy/promote': ['governor'],
  'POST:/api/autonomy/rollback': ['governor'],
  'POST:/api/autonomy/emergency-stop': ['governor'],
};

/**
 * Get identity from request headers or user context
 */
function getIdentity(request: FastifyRequest): { id: string; role: RBACRole } {
  // Try service identity header first
  const serviceIdentity = request.headers['x-service-identity'];
  if (serviceIdentity) {
    return {
      id: serviceIdentity as string,
      role: (serviceIdentity as string).split(':')[1] as RBACRole,
    };
  }

  // Fall back to user identity
  const userId = (request.user as any)?.id || 'anonymous';
  const userRole = (request.user as any)?.role || 'viewer';

  return {
    id: userId,
    role: userRole as RBACRole,
  };
}

/**
 * Check if identity has required role
 */
function hasRole(identity: { id: string; role: RBACRole }, requiredRoles: RBACRole[]): boolean {
  return requiredRoles.includes(identity.role);
}

/**
 * RBAC enforcement middleware
 */
export async function rbacMiddleware(request: FastifyRequest, reply: FastifyReply) {
  const identity = getIdentity(request);
  const operationKey = `${request.method}:${request.url.split('?')[0]}`;

  // Find matching operation rules (check exact match first, then by method)
  let requiredRoles = operationRoles[operationKey];

  if (!requiredRoles) {
    // Check if method is GET (default to viewer)
    if (request.method === 'GET') {
      requiredRoles = ['viewer', 'task_creator', 'learner_service', 'eval_service', 'governor'];
    } else {
      // Default: deny unless explicitly allowed
      return reply.status(403).send({
        error: 'FORBIDDEN',
        message: 'Operation not allowed',
        operation: operationKey,
      });
    }
  }

  // Check if identity has required role
  if (!hasRole(identity, requiredRoles)) {
    console.log(`[RBAC] DENIED: ${identity.id} (${identity.role}) cannot ${operationKey}`);

    // Log denial event for audit
    try {
      await db.query(
        `INSERT INTO autonomy_task_events (
          task_id, event_type, previous_status, new_status, actor_type, actor_id, reason
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)`,
        [
          null, // No specific task
          'escalated',
          'pending',
          'denied',
          'system',
          identity.id,
          `RBAC denied: requires ${requiredRoles.join(' or ')} but user has ${identity.role}`,
        ]
      );
    } catch (error) {
      // Silently continue if audit logging fails
    }

    return reply.status(403).send({
      error: 'INSUFFICIENT_PERMISSIONS',
      message: `This operation requires one of: ${requiredRoles.join(', ')}`,
      userRole: identity.role,
      operation: operationKey,
    });
  }

  console.log(`[RBAC] ALLOWED: ${identity.id} (${identity.role}) executing ${operationKey}`);
}

/**
 * Require governor role (for critical operations)
 */
export async function requireGovernor(request: FastifyRequest, reply: FastifyReply) {
  const identity = getIdentity(request);

  if (identity.role !== 'governor') {
    console.log(`[RBAC] DENIED GOVERNOR-ONLY: ${identity.id} (${identity.role})`);

    return reply.status(403).send({
      error: 'GOVERNOR_REQUIRED',
      message: 'This operation requires governor privileges',
      userRole: identity.role,
    });
  }
}

/**
 * Require learner_service or governor role (for learner operations)
 */
export async function requireLearnerService(request: FastifyRequest, reply: FastifyReply) {
  const identity = getIdentity(request);

  if (identity.role !== 'learner_service' && identity.role !== 'governor') {
    return reply.status(403).send({
      error: 'SERVICE_REQUIRED',
      message: 'This operation requires learner_service role',
      userRole: identity.role,
    });
  }
}
