export const AGENTCO_CAPABILITY_PROTOCOL_VERSION = 'agentco-capability-v1' as const;

export type CapabilityStatus =
  | 'completed'
  | 'failed'
  | 'timed_out'
  | 'cancelled'
  | 'denied'
  | 'budget_exceeded'
  | 'unsupported'
  | 'partially_completed';

export type CapabilityTaskType =
  | 'reasoning'
  | 'planning'
  | 'evidence_evaluation'
  | 'claim_grounding'
  | 'structured_transformation'
  | 'safe_tool_selection'
  | 'data_analysis'
  | 'software_engineering'
  | 'cross_domain_synthesis';

export interface CapabilityRequest {
  protocol_version: typeof AGENTCO_CAPABILITY_PROTOCOL_VERSION;
  request_id: string;
  attempt_id: string;
  actor: { id: string; type?: string; [key: string]: unknown };
  tenant: string;
  task_type: CapabilityTaskType;
  prompt: string;
  structured_input?: Record<string, unknown>;
  context?: Record<string, unknown>;
  memory_policy?: Record<string, unknown>;
  tool_allowlist?: string[];
  provider_policy?: Record<string, unknown>;
  budget: Record<string, unknown>;
  deadline?: string | null;
  idempotency_key?: string | null;
  authorization_context: Record<string, unknown>;
  trace_context?: Record<string, unknown>;
}

export interface CapabilityResponse {
  protocol_version: typeof AGENTCO_CAPABILITY_PROTOCOL_VERSION;
  request_id: string;
  attempt_id: string;
  status: CapabilityStatus;
  answer: unknown;
  structured_output: Record<string, unknown>;
  confidence: number | null;
  evidence: unknown[];
  citations: unknown[];
  tool_calls: unknown[];
  memory_events: unknown[];
  authorization_events: unknown[];
  budget_usage: Record<string, unknown>;
  provider: string | null;
  model: string | null;
  latency: Record<string, unknown>;
  resource_usage: Record<string, unknown>;
  failure: Record<string, unknown> | null;
  recovery: Record<string, unknown>;
  audit_references: unknown[];
}
