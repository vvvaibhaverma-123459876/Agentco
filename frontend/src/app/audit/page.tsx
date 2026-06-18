'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AuditEntry, RISK_COLORS } from '@/types';

type IntegrityResult = { valid: boolean; broken_at?: string };

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    agent_id: '',
    risk_level: '',
    human_approved: '',
    date_from: '',
    date_to: '',
  });
  const [integrity, setIntegrity] = useState<IntegrityResult | null>(null);
  const [integrityLoading, setIntegrityLoading] = useState(false);
  const [hoveredHash, setHoveredHash] = useState<string | null>(null);

  const load = () => {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v));
    api.audit
      .list(params)
      .then((r: { entries: AuditEntry[]; count: number }) => setEntries(r.entries))
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [filters]);

  const verifyIntegrity = async () => {
    setIntegrityLoading(true);
    try {
      const r: IntegrityResult = await api.audit.verifyIntegrity();
      setIntegrity(r);
    } catch {
      setIntegrity(null);
    } finally {
      setIntegrityLoading(false);
    }
  };

  return (
    <div className="p-6">
      {/* Tamper-evident banner */}
      <div className="bg-gray-900 text-gray-100 rounded-lg px-5 py-3 mb-6 text-sm flex items-center gap-3">
        <span className="text-green-400 text-lg">⛓</span>
        <span>
          The audit log is <strong>hash-chained and tamper-evident</strong>. Every entry links to the previous one.
          No entry can be deleted or modified without breaking the chain.
        </span>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-gray-500 mt-1">Immutable record of every agent decision</p>
        </div>

        <div className="flex items-center gap-3">
          {integrity && (
            <span className={`text-sm font-medium px-3 py-1.5 rounded-md ${
              integrity.valid
                ? 'bg-green-100 text-green-700'
                : 'bg-red-100 text-red-700'
            }`}>
              {integrity.valid
                ? '✓ Chain integrity PASS'
                : `✗ Chain FAIL — broken at: ${integrity.broken_at}`}
            </span>
          )}
          <button
            onClick={verifyIntegrity}
            disabled={integrityLoading}
            className="text-sm px-4 py-1.5 bg-gray-900 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
          >
            {integrityLoading ? 'Verifying...' : 'Verify Chain Integrity'}
          </button>
        </div>
      </div>

      {/* Filter controls */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          placeholder="Filter by agent ID..."
          value={filters.agent_id}
          onChange={e => setFilters(f => ({ ...f, agent_id: e.target.value }))}
          className="border border-gray-200 rounded-md px-3 py-1.5 text-sm"
        />
        <select
          value={filters.risk_level}
          onChange={e => setFilters(f => ({ ...f, risk_level: e.target.value }))}
          className="border border-gray-200 rounded-md px-3 py-1.5 text-sm"
        >
          <option value="">All risk levels</option>
          {['low', 'medium', 'high', 'critical'].map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
        <select
          value={filters.human_approved}
          onChange={e => setFilters(f => ({ ...f, human_approved: e.target.value }))}
          className="border border-gray-200 rounded-md px-3 py-1.5 text-sm"
        >
          <option value="">All approvals</option>
          <option value="true">Human approved</option>
          <option value="false">Autonomous</option>
        </select>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">From</label>
          <input
            type="date"
            value={filters.date_from}
            onChange={e => setFilters(f => ({ ...f, date_from: e.target.value }))}
            className="border border-gray-200 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">To</label>
          <input
            type="date"
            value={filters.date_to}
            onChange={e => setFilters(f => ({ ...f, date_to: e.target.value }))}
            className="border border-gray-200 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              {['Log ID', 'Agent', 'Action', 'Confidence', 'Risk', 'Timestamp', 'Chain Hash'].map(h => (
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
                <td className="px-4 py-2 text-xs text-gray-400 font-mono">{entry.log_id?.slice(0, 8)}</td>
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
                <td className="px-4 py-2 text-xs text-gray-400 font-mono">
                  {new Date(entry.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-2 relative">
                  <span
                    className="font-mono text-xs text-gray-400 cursor-default"
                    onMouseEnter={() => setHoveredHash(entry.log_id)}
                    onMouseLeave={() => setHoveredHash(null)}
                  >
                    {(entry as { chain_hash?: string }).chain_hash?.slice(0, 8) || '—'}
                  </span>
                  {hoveredHash === entry.log_id && (entry as { chain_hash?: string }).chain_hash && (
                    <div className="absolute z-10 bottom-full left-0 mb-1 bg-gray-900 text-gray-100 text-xs font-mono px-3 py-2 rounded shadow-lg whitespace-nowrap">
                      {(entry as { chain_hash?: string }).chain_hash}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
