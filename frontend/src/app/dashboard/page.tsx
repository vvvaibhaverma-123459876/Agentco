'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { Agent, DEPARTMENTS, STATUS_COLORS } from '@/types';

const DEPT_LABELS: Record<string, string> = {
  executive: 'Executive', product: 'Product', engineering: 'Engineering',
  design: 'Design', sales: 'Sales', marketing: 'Marketing',
  customer_experience: 'Customer Experience', people_ops: 'People Ops', legal: 'Legal & Compliance',
};

export default function DashboardPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.agents.list()
      .then((r: { agents: Agent[]; count: number }) => setAgents(r.agents))
      .catch(console.error)
      .finally(() => setLoading(false));

    const interval = setInterval(() => {
      api.agents.list().then((r: { agents: Agent[]; count: number }) => setAgents(r.agents)).catch(console.error);
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const byDept = agents.reduce<Record<string, Agent[]>>((acc, a) => {
    (acc[a.department] ??= []).push(a);
    return acc;
  }, {});

  const activeCount = agents.filter(a => a.state.status === 'active').length;
  const errorCount = agents.filter(a => a.state.status === 'error').length;

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agent Status Dashboard</h1>
        <p className="text-gray-500 mt-1">Configured agent registry. Status: PARTIAL.</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Agents', value: agents.length, color: 'text-gray-900' },
          { label: 'Active', value: activeCount, color: 'text-green-600' },
          { label: 'Idle', value: agents.filter(a => a.state.status === 'idle').length, color: 'text-gray-500' },
          { label: 'Errors', value: errorCount, color: 'text-red-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className={`text-3xl font-bold ${color}`}>{value}</div>
            <div className="text-sm text-gray-500 mt-1">{label}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading agents...</div>
      ) : (
        <div className="space-y-6">
          {DEPARTMENTS.map(dept => {
            const deptAgents = byDept[dept] ?? [];
            if (!deptAgents.length) return null;
            return (
              <div key={dept} className="bg-white rounded-lg border border-gray-200">
                <div className="px-4 py-3 border-b border-gray-100">
                  <h2 className="font-semibold text-gray-800">{DEPT_LABELS[dept]}</h2>
                </div>
                <div className="divide-y divide-gray-50">
                  {deptAgents.map(agent => (
                    <div key={agent.id} className="px-4 py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[agent.state.status]}`} />
                        <div>
                          <div className="text-sm font-medium text-gray-900">{agent.id}</div>
                          <div className="text-xs text-gray-400">{agent.model} · v{agent.state.prompt_version ?? '1.0.0'}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span className={`px-2 py-0.5 rounded-full font-medium ${
                          agent.state.lifecycle_state === 'production' ? 'bg-green-50 text-green-700' :
                          agent.state.lifecycle_state === 'canary' ? 'bg-yellow-50 text-yellow-700' :
                          'bg-gray-50 text-gray-600'
                        }`}>{agent.state.lifecycle_state}</span>
                        <span>{agent.state.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
