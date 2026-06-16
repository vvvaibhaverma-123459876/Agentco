'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { OverrideRequest, RISK_COLORS } from '@/types';

function timeLeft(expiresAt: string): string {
  const ms = new Date(expiresAt).getTime() - Date.now();
  if (ms <= 0) return 'OVERDUE';
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  return `${h}h ${m}m`;
}

export default function OverridePage() {
  const [items, setItems] = useState<OverrideRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<string | null>(null);

  const load = () => {
    api.overrides.list().then(r => setItems(r.items)).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);

  const resolve = async (id: string, resolution: 'approved' | 'rejected') => {
    setResolving(id);
    try {
      await api.overrides.resolve(id, resolution, 'human-governor');
      load();
    } finally {
      setResolving(null);
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Human Override Queue</h1>
        <p className="text-gray-500 mt-1">Actions paused pending your decision</p>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading override queue...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <div className="text-4xl mb-3">✓</div>
          <div className="text-gray-500">No pending approvals</div>
        </div>
      ) : (
        <div className="space-y-4">
          {items.map(item => (
            <div key={item.request_id} className={`bg-white rounded-lg border-2 p-5 ${
              item.risk_level === 'critical' ? 'border-red-300' : 'border-orange-200'
            }`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${RISK_COLORS[item.risk_level]}`}>
                      {item.risk_level.toUpperCase()}
                    </span>
                    <span className="font-semibold text-gray-900">{item.action}</span>
                  </div>
                  <div className="text-sm text-gray-500 mt-1">Agent: <strong>{item.agent_id}</strong></div>
                </div>
                <div className={`text-sm font-mono ${
                  timeLeft(item.expires_at) === 'OVERDUE' ? 'text-red-600 font-bold' : 'text-gray-500'
                }`}>
                  SLA: {timeLeft(item.expires_at)}
                </div>
              </div>

              <details className="mb-4">
                <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700">View context</summary>
                <pre className="mt-2 text-xs bg-gray-50 rounded p-3 overflow-auto max-h-40">
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
          ))}
        </div>
      )}
    </div>
  );
}
