import type { Agent, AuditEntry, OverrideRequest } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:3001';

type QueryParams = Record<string, string | number | boolean | undefined>;

function withQuery(path: string, params?: QueryParams): string {
  const url = new URL(path, API_BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path.startsWith('http') ? path : `${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  agents: {
    list: () => request<{ agents: Agent[]; count: number }>('/api/agents'),
  },
  audit: {
    list: (params?: QueryParams) => request<{ entries: AuditEntry[]; count: number }>(withQuery('/api/audit', params)),
    verifyIntegrity: () => request<{ valid: boolean; broken_at?: string }>('/api/audit/integrity'),
  },
  overrides: {
    list: () => request<{ items: OverrideRequest[]; count: number }>('/api/overrides'),
    resolve: (
      requestId: string,
      resolution: 'approved' | 'rejected',
      resolvedBy: string,
    ) => request<{ ok: boolean }>(`/api/overrides/${requestId}/resolve`, {
      method: 'POST',
      body: JSON.stringify({ resolution, resolved_by: resolvedBy }),
    }),
  },
};
