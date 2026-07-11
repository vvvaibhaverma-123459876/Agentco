import type { Agent, AuditEntry, OverrideRequest } from '@/types';
import { agentcoAuthHeaders } from './api/auth';
import { apiUrl } from './api/url';

type QueryValue = string | number | boolean | undefined | null;

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

async function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function isRetryableStatus(status: number): boolean {
  return status === 408 || status === 429 || status >= 500;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  params?: Record<string, QueryValue>,
): Promise<T> {
  const maxRetries = 3;
  const initialDelayMs = 200;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const headers = agentcoAuthHeaders(options.headers);
      headers.set('Accept', 'application/json');

      if (options.body && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json');
      }

      const method = options.method?.toUpperCase() ?? 'GET';

      const response = await fetch(apiUrl(path, toQuery(params)), {
        ...options,
        headers,
      });

      if (!response.ok) {
        const body = await response.text();
        const error = new Error(`${method} ${path} failed: ${response.status} ${body}`);
        (error as any).status = response.status;

        if (attempt < maxRetries && isRetryableStatus(response.status)) {
          const delay = initialDelayMs * Math.pow(2, attempt);
          console.warn(`Request attempt ${attempt + 1} failed (${response.status}), retrying in ${delay}ms`);
          lastError = error;
          await sleep(delay);
          continue;
        }

        throw error;
      }

      return response.json() as Promise<T>;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));

      if (attempt < maxRetries && (err instanceof TypeError || (err as any).status >= 500)) {
        const delay = initialDelayMs * Math.pow(2, attempt);
        console.warn(`Request attempt ${attempt + 1} failed, retrying in ${delay}ms:`, lastError.message);
        await sleep(delay);
      } else {
        throw lastError;
      }
    }
  }

  throw lastError || new Error('Request failed after retries');
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
