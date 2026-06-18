'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { OverrideRequest, RISK_COLORS } from '@/types';

function timeLeft(deadline: string): { label: string; urgent: boolean } {
  const ms = new Date(deadline).getTime() - Date.now();
  if (ms <= 0) return { label: 'OVERDUE', urgent: true };
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  const s = Math.floor((ms % 60000) / 1000);
  if (h === 0 && m < 5) return { label: `${m}m ${s}s`, urgent: true };
  return { label: `${h}h ${m}m`, urgent: false };
}

export default function OverridePage() {
  const [items, setItems] = useState<OverrideRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());

  const load = () => {
    api.overrides
      .list()
      .then((r: { items: OverrideRequest[]; count: number }) => setItems(r.items))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => { clearInterval(t); clearInterval(tick); };
  }, []);

  const resolve = async (id: string, resolution: 'approved' | 'rejected') => {
    setResolving(id);
    try {
      await api.overrides.resolve(id, resolution, 'human-governor');
      load();
    } finally {
      setResolving(null);
    }
  };

  // Split pending vs resolved
  const pending = items.filter(i => !['approved', 'rejected'].includes((i as { status?: string }).status || ''));
  const resolved = items.filter(i => ['approved', 'rejected'].includes((i as { status?: string }).status || ''));

  void now; // used to trigger re-render for countdown

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Human Override Queue</h1>
        <p className="text-gray-500 mt-1">Actions paused pending your decision</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading override queue...</div>
      ) : pending.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <div className="text-4xl mb-3">✓</div>
          <div className="text-gray-500">No pending approvals</div>
        </div>
      ) : (
        <div className="space-y-4 mb-8">
          {pending.map(item => {
            const sla = timeLeft(item.expires_at || item.expires_at || '');
            return (
              <div
                key={item.request_id}
                className={`bg-white rounded-lg border-2 p-5 ${
                  item.risk_level === 'critical' ? 'border-red-300' : 'border-orange-200'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${RISK_COLORS[item.risk_level]}`}>
                        {item.risk_level.toUpperCase()}
                      </span>
                      <span className="font-semibold text-gray-900">{item.action}</span>
                    </div>
                    <div className="text-sm text-gray-500 mt-1">
                      Agent: <strong>{item.agent_id}</strong>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-gray-400 mb-1">SLA Countdown</div>
                    <div className={`text-sm font-mono font-semibold ${
                      sla.urgent ? 'text-red-600' : 'text-gray-700'
                    }`}>
                      {sla.label}
                    </div>
                    {(item.expires_at || item.expires_at) && (
                      <div className="text-xs text-gray-400 mt-0.5">
                        Deadline: {new Date(item.expires_at || item.expires_at || '').toLocaleString()}
                      </div>
                    )}
                  </div>
                </div>

                {/* Context display */}
                <details className="mb-4" open={item.risk_level === 'critical'}>
                  <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700 select-none">
                    View context
                  </summary>
                  <pre className="mt-2 text-xs bg-gray-50 rounded p-3 overflow-auto max-h-48 border border-gray-100">
                    {JSON.stringify(item.context, null, 2)}
                  </pre>
                </details>

                <div className="flex gap-3">
                  <button
                    onClick={() => resolve(item.request_id, 'approved')}
                    disabled={resolving === item.request_id}
                    className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => resolve(item.request_id, 'rejected')}
                    disabled={resolving === item.request_id}
                    className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Override History */}
      {resolved.length > 0 && (
        <div className="mt-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-3">Override History</h2>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Request ID', 'Agent', 'Action', 'Risk', 'Resolution', 'Context'].map(h => (
                    <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {resolved.map(item => (
                  <tr key={item.request_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-400">{item.request_id?.slice(0, 8)}</td>
                    <td className="px-4 py-2 font-medium">{item.agent_id}</td>
                    <td className="px-4 py-2 text-gray-600">{item.action}</td>
                    <td className="px-4 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${RISK_COLORS[item.risk_level]}`}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {(item as { status?: string }).status === 'approved' ? (
                        <span className="text-green-600 text-xs font-medium">✓ Approved</span>
                      ) : (
                        <span className="text-red-600 text-xs font-medium">✗ Rejected</span>
                      )}
                    </td>
                    <td className="px-4 py-2 max-w-xs">
                      <details>
                        <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">View</summary>
                        <pre className="mt-1 text-xs bg-gray-50 rounded p-2 overflow-auto max-h-24">
                          {JSON.stringify(item.context, null, 2)}
                        </pre>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
