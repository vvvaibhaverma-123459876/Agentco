'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AuditEntry, RISK_COLORS } from '@/types';

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ agent_id: '', risk_level: '', human_approved: '' });

  const load = () => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    api.audit.list(params).then((r: { entries: AuditEntry[]; count: number }) => setEntries(r.entries)).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filters]);

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-gray-500 mt-1">Immutable record of every agent decision</p>
        </div>
        <button
          onClick={() => api.audit.verifyIntegrity().then((r: { valid: boolean; broken_at?: string }) => alert(r.valid ? '✓ Chain integrity valid' : `⚠ Chain broken at: ${r.broken_at}`))}
          className="text-sm px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Verify Chain
        </button>
      </div>

      <div className="flex gap-3 mb-4">
        <input placeholder="Filter by agent..." value={filters.agent_id} onChange={e => setFilters(f => ({ ...f, agent_id: e.target.value }))}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm" />
        <select value={filters.risk_level} onChange={e => setFilters(f => ({ ...f, risk_level: e.target.value }))}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm">
          <option value="">All risk levels</option>
          {['low','medium','high','critical'].map(r => <option key={r} value={r}>{r}</option>)}
        </select>
        <select value={filters.human_approved} onChange={e => setFilters(f => ({ ...f, human_approved: e.target.value }))}
          className="border border-gray-300 rounded-md px-3 py-1.5 text-sm">
          <option value="">All approvals</option>
          <option value="true">Human approved</option>
          <option value="false">Autonomous</option>
        </select>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Timestamp', 'Agent', 'Action', 'Confidence', 'Risk', 'Approved', 'Output'].map(h => (
                <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">Loading...</td></tr>
            ) : entries.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">No entries</td></tr>
            ) : entries.map(entry => (
              <tr key={entry.log_id} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-xs text-gray-400 font-mono">
                  {new Date(entry.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2 font-medium">{entry.agent_id}</td>
                <td className="px-4 py-2 text-gray-600">{entry.action_type}</td>
                <td className="px-4 py-2">
                  <span className={entry.confidence_score >= 0.7 ? 'text-green-600' : 'text-red-600'}>
                    {(entry.confidence_score * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="px-4 py-2">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${RISK_COLORS[entry.risk_level]}`}>
                    {entry.risk_level}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {entry.human_approved ? '✓ Human' : '— Auto'}
                </td>
                <td className="px-4 py-2 text-gray-500 max-w-xs truncate">{entry.output_summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
