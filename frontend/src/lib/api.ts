import type { Agent, AuditEntry, OverrideRequest } from '@/types';

type QueryValue = string | number | boolean | undefined | null;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';
const API_KEY = process.env.NEXT_PUBLIC_AGENTCO_API_KEY;

function toQuery(params?: Record<string, QueryValue>): string {
  if (!params) return '';
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  params?: Record<string, QueryValue>,
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set('Accept', 'application/json');

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const method = options.method?.toUpperCase() ?? 'GET';
  if (API_KEY && !['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    headers.set('x-api-key', API_KEY);
  }

  const response = await fetch(`${API_BASE_URL}${path}${toQuery(params)}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${method} ${path} failed: ${response.status} ${body}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  agents: {
    list: () => request<{ agents: Agent[]; count: number }>('/api/agents'),
    get: (id: string) => request<Agent>(`/api/agents/${encodeURIComponent(id)}`),
    dispatch: (id: string, task_type: string, payload: Record<string, unknown> = {}) =>
      request<{ task_id: string; status: string }>(`/api/agents/${encodeURIComponent(id)}/dispatch`, {
        method: 'POST',
        body: JSON.stringify({ task_type, payload }),
      }),
    task: (taskId: string) => request(`/api/agents/tasks/${encodeURIComponent(taskId)}`),
    tasks: () => request('/api/agents/tasks'),
  },
  audit: {
    list: (params?: Record<string, QueryValue>) => request<{ entries: AuditEntry[]; count: number }>('/api/audit', {}, params),
    verifyIntegrity: () => request<{ valid: boolean; broken_at?: string }>('/api/audit/integrity'),
  },
  overrides: {
    list: (params?: Record<string, QueryValue>) => request<{ items: OverrideRequest[]; count: number }>('/api/overrides', {}, params),
    overdue: () => request<{ items: OverrideRequest[]; count: number }>('/api/overrides/overdue'),
    resolve: (requestId: string, resolution: 'approved' | 'rejected', resolved_by: string, notes?: string) =>
      request<OverrideRequest>(`/api/overrides/${encodeURIComponent(requestId)}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ resolution, resolved_by, notes }),
      }),
    enqueue: (agent_id: string, action: string, risk_level: 'high' | 'critical', context: Record<string, unknown>) =>
      request<OverrideRequest>('/api/overrides', {
        method: 'POST',
        body: JSON.stringify({ agent_id, action, risk_level, context }),
      }),
  },
  validation: {
    reports: () => request<{ release_passes: boolean; reports: Array<{ benchmark: string; evidence_quality: string; score: number; threshold: number; status: string }> }>('/api/validation/reports'),
  },
};
