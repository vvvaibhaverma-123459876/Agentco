'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

interface Stats {
  predictions_total: number;
  predictions_resolved_true: number;
  predictions_resolved_false: number;
  predictions_pending: number;
}

interface Prediction {
  prediction_id: string;
  claim: string;
  producing_agent_id: string;
  probability: number;
  resolved: boolean;
  resolved_outcome?: string;
}

interface Task {
  task_id: string;
  agent_id: string;
  task_type: string;
  status: string;
  result?: string;
  created_at: string;
}

const AGENT_IDS = Array.from({ length: 29 }, (_, i) => `agent-${String(i + 1).padStart(3, '0')}`);

function OutcomeBadge({ resolved, outcome }: { resolved: boolean; outcome?: string }) {
  if (!resolved)
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-yellow-100 text-yellow-700">PENDING</span>
    );
  if (outcome === 'true' || outcome === 'TRUE')
    return (
      <span className="px-2 py-0.5 rounded text-xs bg-green-100 text-green-700">TRUE</span>
    );
  return <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-700">FALSE</span>;
}

export default function RunPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [statsError, setStatsError] = useState<string | null>(null);
  const [predsError, setPredsError] = useState<string | null>(null);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Dispatch form state
  const [dispatchAgent, setDispatchAgent] = useState(AGENT_IDS[0]);
  const [taskType, setTaskType] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [dispatchResult, setDispatchResult] = useState<string | null>(null);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  async function loadData() {
    try {
      const s = await apiFetch<Stats>('/api/stats');
      setStats(s);
      setStatsError(null);
    } catch {
      setStatsError('Could not load stats — is the backend running?');
    }
    try {
      const p = await apiFetch<{ predictions: Prediction[] }>(
        '/api/predictions?limit=5&sort=desc'
      );
      setPredictions(p.predictions ?? []);
      setPredsError(null);
    } catch {
      setPredsError('Could not load predictions — is the backend running?');
    }
    try {
      const t = await apiFetch<{ tasks: Task[] }>('/api/agents/tasks');
      setTasks(t.tasks ?? []);
      setTasksError(null);
    } catch {
      setTasksError('Could not load tasks — is the backend running?');
    }
    setLastRefresh(new Date());
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleDispatch(e: React.FormEvent) {
    e.preventDefault();
    if (!taskType.trim()) return;
    setDispatching(true);
    setDispatchResult(null);
    setDispatchError(null);
    try {
      const res = await apiFetch<{ task_id?: string; message?: string }>(
        `/api/agents/${dispatchAgent}/dispatch`,
        {
          method: 'POST',
          body: JSON.stringify({ task_type: taskType }),
        }
      );
      setDispatchResult(
        res.task_id ? `Task dispatched: ${res.task_id}` : res.message ?? 'Dispatched.'
      );
      setTaskType('');
      loadData();
    } catch (err: unknown) {
      setDispatchError(err instanceof Error ? err.message : 'Dispatch failed.');
    } finally {
      setDispatching(false);
    }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Autonomous Run</h1>
        <p className="text-xs text-gray-400 mt-1">
          Last refreshed: {lastRefresh.toLocaleTimeString()} · Auto-refreshes every 30s
        </p>
      </div>

      {/* Status Cards */}
      {statsError ? (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {statsError}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            {
              label: 'Predictions Registered',
              value: stats?.predictions_total,
              color: 'text-blue-600',
            },
            {
              label: 'Resolved True',
              value: stats?.predictions_resolved_true,
              color: 'text-green-600',
            },
            {
              label: 'Resolved False',
              value: stats?.predictions_resolved_false,
              color: 'text-red-600',
            },
            { label: 'Pending', value: stats?.predictions_pending, color: 'text-yellow-600' },
          ].map((c) => (
            <div key={c.label} className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="text-xs text-gray-500 mb-1">{c.label}</p>
              <p className={`text-2xl font-bold ${c.color}`}>
                {c.value != null ? c.value.toLocaleString() : '—'}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Recent Predictions */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Predictions</h2>
        {predsError ? (
          <p className="text-red-600 text-sm">{predsError}</p>
        ) : predictions.length === 0 ? (
          <p className="text-gray-400 text-sm">No predictions yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-100">
                  <th className="pb-2 pr-3 font-medium">Claim</th>
                  <th className="pb-2 pr-3 font-medium">Agent</th>
                  <th className="pb-2 pr-3 font-medium">Probability</th>
                  <th className="pb-2 font-medium">Outcome</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => (
                  <tr key={p.prediction_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 pr-3 text-gray-700 max-w-xs">
                      <span title={p.claim}>
                        {p.claim.length > 80 ? p.claim.slice(0, 80) + '…' : p.claim}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-gray-500 text-xs">{p.producing_agent_id}</td>
                    <td className="py-2 pr-3 text-gray-700">
                      {(p.probability * 100).toFixed(1)}%
                    </td>
                    <td className="py-2">
                      <OutcomeBadge resolved={p.resolved} outcome={p.resolved_outcome} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Run History */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Run History</h2>
        {tasksError ? (
          <p className="text-red-600 text-sm">{tasksError}</p>
        ) : tasks.length === 0 ? (
          <p className="text-gray-400 text-sm">No tasks yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-100">
                  <th className="pb-2 pr-3 font-medium">Task ID</th>
                  <th className="pb-2 pr-3 font-medium">Agent</th>
                  <th className="pb-2 pr-3 font-medium">Type</th>
                  <th className="pb-2 pr-3 font-medium">Status</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((t) => (
                  <tr key={t.task_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 pr-3 font-mono text-xs text-gray-400">
                      {t.task_id.slice(0, 8)}
                    </td>
                    <td className="py-2 pr-3 text-gray-600 text-xs">{t.agent_id}</td>
                    <td className="py-2 pr-3 text-gray-700">{t.task_type}</td>
                    <td className="py-2 pr-3">
                      <span
                        className={`px-2 py-0.5 rounded text-xs ${
                          t.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : t.status === 'failed'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {t.status}
                      </span>
                    </td>
                    <td className="py-2 text-gray-400 text-xs">
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dispatch Task */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Dispatch Task</h2>
        <form onSubmit={handleDispatch} className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Agent</label>
            <select
              value={dispatchAgent}
              onChange={(e) => setDispatchAgent(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {AGENT_IDS.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-500 mb-1">Task Type</label>
            <input
              type="text"
              value={taskType}
              onChange={(e) => setTaskType(e.target.value)}
              placeholder="e.g. generate_prediction"
              className="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={dispatching || !taskType.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {dispatching ? 'Dispatching…' : 'Dispatch Task'}
          </button>
        </form>
        {dispatchResult && (
          <p className="mt-2 text-sm text-green-700 bg-green-50 rounded p-2">{dispatchResult}</p>
        )}
        {dispatchError && (
          <p className="mt-2 text-sm text-red-700 bg-red-50 rounded p-2">{dispatchError}</p>
        )}
      </div>
    </div>
  );
}
