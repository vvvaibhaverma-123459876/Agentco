import type { FastifyRequest } from 'fastify';
import { PublicHttpError } from '../http-errors';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const UUID_PARAM_NAMES = new Set([
  'accountId',
  'assessmentId',
  'canaryId',
  'driftId',
  'entityId',
  'evidenceId',
  'goalId',
  'institutionId',
  'parentGoalId',
  'parentSubGoalId',
  'policyId',
  'requestId',
  'request_id',
  'sourceEvidenceId',
  'task_id',
]);

export function validateUuidPathParams(request: FastifyRequest): void {
  const params = request.params as Record<string, unknown> | undefined;
  if (!params) return;

  for (const [name, value] of Object.entries(params)) {
    if (!UUID_PARAM_NAMES.has(name)) continue;
    if (typeof value !== 'string' || !UUID_RE.test(value)) {
      throw new PublicHttpError(400, 'Invalid path parameter');
    }
  }
}
