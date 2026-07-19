'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { AuditEntry } from '@/types';

function isIncidentCandidate(entry: AuditEntry): boolean {
  const text = `${entry.action_type} ${entry.input_summary} ${entry.output_summary}`.toLowerCase();
  return (
    text.includes('incident') ||
    text.includes('rollback') ||
    text.includes('outage') ||
    text.includes('error') ||
    text.includes('failure') ||
    text.includes('failed')
  );
}

export default function IncidentsPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.audit.list({ limit: 200 })
      .then(result => {
        if (!cancelled) setEntries(result.entries);
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const incidentEntries = useMemo(() => entries.filter(isIncidentCandidate), [entries]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Incident Log</h1>
      <p className="text-gray-500 mt-1">Incident-like audit records with timeline and rollback context when present.</p>

      {error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Unable to load incident evidence: {error}
        </div>
      ) : null}

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm text-gray-500">Audit records sampled</div>
            <div className="mt-1 text-2xl font-bold text-gray-900">{loading ? 'loading...' : entries.length}</div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-500">Incident-like records</div>
            <div className="mt-1 text-2xl font-bold text-gray-900">{loading ? 'loading...' : incidentEntries.length}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 bg-white">
        {loading ? (
          <div className="py-8 text-center text-sm text-gray-400">Loading incident evidence...</div>
        ) : incidentEntries.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-400">
            No incident-like audit records found in the sampled window. This is not proof that no active incidents exist.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50">
              <tr>
                {['Timestamp', 'Agent', 'Action', 'Risk', 'Evidence'].map(header => (
                  <th key={header} className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{header}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {incidentEntries.map(entry => (
                <tr key={entry.log_id}>
                  <td className="px-4 py-2 font-mono text-xs text-gray-400">{new Date(entry.timestamp).toLocaleString()}</td>
                  <td className="px-4 py-2 font-medium text-gray-700">{entry.agent_id}</td>
                  <td className="px-4 py-2 text-gray-600">{entry.action_type}</td>
                  <td className="px-4 py-2 text-gray-600">{entry.risk_level}</td>
                  <td className="max-w-xl truncate px-4 py-2 text-gray-500">{entry.output_summary || entry.input_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
