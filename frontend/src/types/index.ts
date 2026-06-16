export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type AgentLifecycle = 'provisioned' | 'staging' | 'canary' | 'production' | 'deprecated' | 'retired';
export type AgentStatus = 'idle' | 'active' | 'paused' | 'error';
export type OverrideStatus = 'pending' | 'approved' | 'rejected' | 'expired';

export interface Agent {
  id: string;
  department: string;
  model: string;
  state: {
    status: AgentStatus;
    lifecycle_state: AgentLifecycle;
    last_heartbeat?: string;
    active_task_id?: string;
    prompt_version?: string;
  };
}

export interface AuditEntry {
  log_id: string;
  agent_id: string;
  action_type: 'decision' | 'api_call' | 'event_published' | 'escalation';
  input_summary: string;
  output_summary: string;
  confidence_score: number;
  risk_level: RiskLevel;
  human_approved: boolean;
  human_approver_id?: string;
  timestamp: string;
  session_id?: string;
}

export interface OverrideRequest {
  request_id: string;
  agent_id: string;
  action: string;
  risk_level: RiskLevel;
  risk_score: number;
  context: Record<string, unknown>;
  created_at: string;
  sla_hours: number;
  expires_at: string;
  status: OverrideStatus;
  resolved_by?: string;
  resolved_at?: string;
}

export interface AgentEvent {
  event_id: string;
  event_type: string;
  producer_agent_id: string;
  timestamp: string;
  confidence_score: number;
  risk_level: RiskLevel;
  payload: Record<string, unknown>;
}

export interface PerformanceMetric {
  agent_id: string;
  period_start: string;
  period_end: string;
  task_count: number;
  error_rate: number;
  avg_latency_ms: number;
  p99_latency_ms: number;
  avg_confidence: number;
  cost_per_task_usd: number;
}

export const DEPARTMENTS = [
  'executive', 'product', 'engineering', 'design',
  'sales', 'marketing', 'customer_experience', 'people_ops', 'legal'
] as const;

export type Department = typeof DEPARTMENTS[number];

export const RISK_COLORS: Record<RiskLevel, string> = {
  low: 'text-green-600 bg-green-50',
  medium: 'text-yellow-600 bg-yellow-50',
  high: 'text-orange-600 bg-orange-50',
  critical: 'text-red-600 bg-red-50',
};

export const STATUS_COLORS: Record<AgentStatus, string> = {
  idle: 'bg-gray-400',
  active: 'bg-green-500',
  paused: 'bg-yellow-500',
  error: 'bg-red-500',
};
