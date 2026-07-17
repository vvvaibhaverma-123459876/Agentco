import crypto from 'crypto';
import { PublicHttpError } from '../http-errors';
import {
  AGENTCO_CAPABILITY_PROTOCOL_VERSION,
  CapabilityRequest,
  CapabilityResponse,
} from '../types/capability.types';

const attempts = new Map<string, CapabilityResponse & { request: CapabilityRequest; idempotency_key?: string | null }>();

function hash(value: unknown): string {
  return crypto.createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

function confidence(request: CapabilityRequest): number {
  const digest = hash(request);
  return Number((0.55 + (parseInt(digest.slice(0, 4), 16) % 35) / 100).toFixed(3));
}

function permissions(request: CapabilityRequest): Set<string> {
  const raw = request.authorization_context?.permissions;
  return new Set(Array.isArray(raw) ? raw.map(String) : []);
}

function authorize(request: CapabilityRequest) {
  const allowed = Boolean(request.actor?.id) && permissions(request).has('capability:execute');
  return {
    actor_id: request.actor?.id,
    tenant: request.tenant,
    permission: 'capability:execute',
    allowed,
    reason: allowed ? 'authorized' : 'missing capability:execute permission or actor id',
  };
}

function budgetFor(request: CapabilityRequest) {
  const maxWall = Number(request.budget?.max_wall_ms ?? 5000);
  return {
    reserved: true,
    max_wall_ms: maxWall,
    max_provider_calls: Number(request.budget?.max_provider_calls ?? 1),
    max_tool_calls: Number(request.budget?.max_tool_calls ?? request.tool_allowlist?.length ?? 0),
    max_tokens: Number(request.budget?.max_tokens ?? 2048),
    provider_calls: 1,
    tool_calls: 0,
    within_budget: true,
  };
}

function memoryEvents(request: CapabilityRequest) {
  if (!request.memory_policy?.enabled) return [{ event: 'memory_skipped', reason: 'memory_policy_disabled' }];
  const memories = Array.isArray(request.memory_policy.memories) ? request.memory_policy.memories : [];
  return memories
    .filter((item: any) => item?.verified === true)
    .map((item: any) => ({
      event: 'memory_retrieved',
      memory_id: item.id,
      eligible: true,
      relevance: item.relevance ?? 0.5,
      affected_response: Boolean(item.content),
    }));
}

function providerOutput(request: CapabilityRequest) {
  const evidence = [{ type: 'request_prompt_hash', sha256: hash(request.prompt) }];
  if ((request.provider_policy?.provider ?? 'deterministic_local_reference') !== 'deterministic_local_reference') {
    throw new PublicHttpError(422, 'unsupported provider');
  }
  if (request.task_type === 'planning') {
    return {
      answer: 'validated four-step governed plan',
      structured_output: {
        goal: request.prompt,
        ordered_steps: [
          'validate request authority and budget',
          'collect context and evidence',
          'execute allowed tools only when needed',
          'verify auditable output',
        ],
      },
      evidence,
    };
  }
  if (request.task_type === 'evidence_evaluation') {
    const rows = Array.isArray(request.structured_input?.evidence) ? request.structured_input.evidence as any[] : [];
    const support = rows.filter(row => row?.stance === 'support').length;
    const contradict = rows.filter(row => row?.stance === 'contradict').length;
    const conclusion = support > contradict ? 'supported' : contradict > support ? 'contradicted' : 'uncertain';
    return {
      answer: conclusion,
      structured_output: {
        conclusion,
        accepted_evidence: rows.filter(row => Number(row?.reliability ?? 0) >= 0.6).map(row => row.id),
        rejected_evidence: rows.filter(row => Number(row?.reliability ?? 0) < 0.6).map(row => row.id),
      },
      evidence,
    };
  }
  return {
    answer: `deterministic ${request.task_type} response for ${request.prompt.length} prompt characters`,
    structured_output: { task_type: request.task_type, prompt_hash: hash(request.prompt) },
    evidence,
  };
}

export const capabilityRuntime = {
  execute(request: CapabilityRequest): CapabilityResponse {
    if (request.protocol_version !== AGENTCO_CAPABILITY_PROTOCOL_VERSION) {
      throw new PublicHttpError(400, 'Invalid request');
    }
    if (request.idempotency_key) {
      const existing = attempts.get(request.attempt_id);
      if (existing?.idempotency_key === request.idempotency_key) return { ...existing, idempotent_replay: true } as any;
    }
    const started = Date.now();
    const auth = authorize(request);
    const budget = budgetFor(request);
    const base = {
      protocol_version: AGENTCO_CAPABILITY_PROTOCOL_VERSION,
      request_id: request.request_id,
      attempt_id: request.attempt_id,
      authorization_events: [auth],
      budget_usage: budget,
      memory_events: memoryEvents(request),
      citations: [],
      tool_calls: [],
      audit_references: [{ type: 'backend_memory_attempt', id: request.attempt_id }],
      resource_usage: { measurement_method: 'process_wall_clock_only' },
    };
    let response: CapabilityResponse;
    if (!auth.allowed) {
      response = {
        ...base,
        status: 'denied',
        answer: null,
        structured_output: {},
        confidence: null,
        evidence: [],
        provider: null,
        model: null,
        latency: { wall_clock_ms: Date.now() - started },
        failure: { type: 'denied', message: auth.reason, recoverable: false },
        recovery: { retryable: false, terminal: true },
      };
    } else if (budget.max_provider_calls < 1) {
      response = {
        ...base,
        status: 'budget_exceeded',
        answer: null,
        structured_output: {},
        confidence: null,
        evidence: [],
        provider: null,
        model: null,
        latency: { wall_clock_ms: Date.now() - started },
        failure: { type: 'budget_exceeded', message: 'provider call budget is zero', recoverable: false },
        recovery: { retryable: false, terminal: true },
      };
    } else {
      const output = providerOutput(request);
      response = {
        ...base,
        status: 'completed',
        answer: output.answer,
        structured_output: output.structured_output,
        confidence: confidence(request),
        evidence: output.evidence,
        provider: 'deterministic_local_reference',
        model: 'agentco-deterministic-reference-v1',
        latency: { wall_clock_ms: Date.now() - started },
        failure: null,
        recovery: { retryable: false, terminal: true },
      };
    }
    attempts.set(request.attempt_id, { ...response, request, idempotency_key: request.idempotency_key });
    return response;
  },

  get(attemptId: string) {
    return attempts.get(attemptId) ?? null;
  },

  cancel(attemptId: string) {
    const existing = attempts.get(attemptId);
    if (!existing) throw new PublicHttpError(404, 'not found');
    if (existing.status === 'completed') return existing;
    const cancelled = { ...existing, status: 'cancelled' as const };
    attempts.set(attemptId, cancelled);
    return cancelled;
  },

  resetForTests() {
    attempts.clear();
  },
};
