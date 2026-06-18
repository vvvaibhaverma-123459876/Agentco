'use client';

import { useState, useCallback } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

interface Prediction {
  prediction_id: string;
  claim: string;
  producing_agent_id: string;
  domain: string;
  probability: number;
  resolved: boolean;
  resolved_outcome?: string;
  registered_at: string;
  resolution_criterion?: string;
  resolution_date?: string;
  ground_truth_source?: string;
  brier_score?: number;
  log_score?: number;
}

interface PredictionsResponse {
  predictions: Prediction[];
  count: number;
}

function OutcomeBadge({ resolved, outcome }: { resolved: boolean; outcome?: string }) {
  if (!resolved)
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-700">
        PENDING
      </span>
    );
  if (outcome === 'true' || outcome === 'TRUE')
    return (
      <span className="px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
        TRUE
      </span>
    );
  return (
    <span className="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">FALSE</span>
  );
}

const LIMIT = 25;

export default function LedgerPage() {
  const [agentFilter, setAgentFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState('all');
  const [searchText, setSearchText] = useState('');
  const [offset, setOffset] = useState(0);

  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);

  const buildQS = useCallback(
    (off: number) => {
      const params: Record<string, string> = { limit: String(LIMIT), offset: String(off) };
      if (agentFilter.trim()) params.agent_id = agentFilter.trim();
      if (domainFilter.trim()) params.domain = domainFilter.trim();
      if (outcomeFilter !== 'all') params.outcome = outcomeFilter;
      if (searchText.trim()) params.search = searchText.trim();
      return '?' + new URLSearchParams(params).toString();
    },
    [agentFilter, domainFilter, outcomeFilter, searchText]
  );

  async function fetchPredictions(off: number) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<PredictionsResponse>(`/api/predictions${buildQS(off)}`);
      setPredictions(data.predictions ?? []);
      setTotal(data.count ?? 0);
      setHasLoaded(true);
    } catch {
      setError('Could not load data — is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  function handleApply() {
    setOffset(0);
    fetchPredictions(0);
  }

  function handlePrev() {
    const newOffset = Math.max(0, offset - LIMIT);
    setOffset(newOffset);
    fetchPredictions(newOffset);
  }

  function handleNext() {
    const newOffset = offset + LIMIT;
    setOffset(newOffset);
    fetchPredictions(newOffset);
  }

  function exportCSV() {
    if (predictions.length === 0) return;
    const headers = [
      'prediction_id',
      'claim',
      'producing_agent_id',
      'domain',
      'probability',
      'resolved',
      'resolved_outcome',
      'registered_at',
    ];
    const rows = predictions.map((p) =>
      [
        p.prediction_id,
        `"${p.claim.replace(/"/g, '""')}"`,
        p.producing_agent_id,
        p.domain,
        p.probability,
        p.resolved,
        p.resolved_outcome ?? '',
        p.registered_at,
      ].join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const url = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'predictions.csv';
    a.click();
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-amber-800 font-medium">
          This ledger is immutable. No prediction can be edited or deleted. Every entry is
          hash-chained and tamper-evident.
        </p>
      </div>

      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-gray-900">Prediction Ledger</h1>
        <button
          onClick={exportCSV}
          disabled={predictions.length === 0}
          className="border border-gray-300 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Export CSV
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Agent ID</label>
            <input
              type="text"
              value={agentFilter}
              onChange={(e) => setAgentFilter(e.target.value)}
              placeholder="agent-001"
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Domain</label>
            <input
              type="text"
              value={domainFilter}
              onChange={(e) => setDomainFilter(e.target.value)}
              placeholder="economics"
              className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Outcome</label>
            <select
              value={outcomeFilter}
              onChange={(e) => setOutcomeFilter(e.target.value)}
              className="border border-gray-300 rounded px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="true">True</option>
              <option value="false">False</option>
              <option value="pending">Pending</option>
            </select>
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-xs text-gray-500 mb-1">Search</label>
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search claims…"
              className="border border-gray-300 rounded px-3 py-2 text-sm w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={handleApply}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Apply
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-4">
          {error}
        </div>
      )}

      {!hasLoaded && !loading && (
        <div className="text-gray-400 text-sm text-center py-12">
          Apply filters to load predictions.
        </div>
      )}

      {loading && (
        <div className="text-gray-400 text-sm text-center py-12">Loading…</div>
      )}

      {hasLoaded && !loading && predictions.length === 0 && !error && (
        <div className="text-gray-400 text-sm text-center py-12">
          No predictions match your filters.
        </div>
      )}

      {!loading && predictions.length > 0 && (
        <>
          <div className="text-xs text-gray-400 mb-2">
            Showing {offset + 1}–{Math.min(offset + LIMIT, total)} of {total.toLocaleString()} predictions
          </div>
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden mb-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-100 bg-gray-50">
                  <th className="px-3 py-2 font-medium">ID</th>
                  <th className="px-3 py-2 font-medium">Claim</th>
                  <th className="px-3 py-2 font-medium">Agent</th>
                  <th className="px-3 py-2 font-medium">Domain</th>
                  <th className="px-3 py-2 font-medium">Prob</th>
                  <th className="px-3 py-2 font-medium">Outcome</th>
                  <th className="px-3 py-2 font-medium">Registered</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((p) => (
                  <>
                    <tr
                      key={p.prediction_id}
                      onClick={() =>
                        setExpandedId(expandedId === p.prediction_id ? null : p.prediction_id)
                      }
                      className="border-b border-gray-50 hover:bg-blue-50 cursor-pointer"
                    >
                      <td className="px-3 py-2 font-mono text-xs text-gray-400">
                        {p.prediction_id.slice(0, 8)}
                      </td>
                      <td className="px-3 py-2 text-gray-700 max-w-xs">
                        <span title={p.claim}>
                          {p.claim.length > 80 ? p.claim.slice(0, 80) + '…' : p.claim}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-gray-500 text-xs">{p.producing_agent_id}</td>
                      <td className="px-3 py-2 text-gray-500 text-xs">{p.domain}</td>
                      <td className="px-3 py-2 text-gray-700">
                        {(p.probability * 100).toFixed(1)}%
                      </td>
                      <td className="px-3 py-2">
                        <OutcomeBadge resolved={p.resolved} outcome={p.resolved_outcome} />
                      </td>
                      <td className="px-3 py-2 text-gray-400 text-xs">
                        {new Date(p.registered_at).toLocaleDateString()}
                      </td>
                    </tr>
                    {expandedId === p.prediction_id && (
                      <tr key={`${p.prediction_id}-expanded`} className="bg-blue-50">
                        <td colSpan={7} className="px-4 py-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="text-xs text-gray-400 mb-1">Full Claim</p>
                              <p className="text-gray-700">{p.claim}</p>
                            </div>
                            {p.resolution_criterion && (
                              <div>
                                <p className="text-xs text-gray-400 mb-1">Resolution Criterion</p>
                                <p className="text-gray-700">{p.resolution_criterion}</p>
                              </div>
                            )}
                            {p.resolution_date && (
                              <div>
                                <p className="text-xs text-gray-400 mb-1">Resolution Date</p>
                                <p className="text-gray-700">
                                  {new Date(p.resolution_date).toLocaleDateString()}
                                </p>
                              </div>
                            )}
                            {p.ground_truth_source && (
                              <div>
                                <p className="text-xs text-gray-400 mb-1">Ground Truth Source</p>
                                <p className="text-gray-700">{p.ground_truth_source}</p>
                              </div>
                            )}
                            {p.brier_score != null && (
                              <div>
                                <p className="text-xs text-gray-400 mb-1">Brier Score</p>
                                <p className="text-gray-700">{p.brier_score.toFixed(4)}</p>
                              </div>
                            )}
                            {p.log_score != null && (
                              <div>
                                <p className="text-xs text-gray-400 mb-1">Log Score</p>
                                <p className="text-gray-700">{p.log_score.toFixed(4)}</p>
                              </div>
                            )}
                            <div className="md:col-span-2">
                              <p className="text-xs text-gray-400 mb-1">Chain Proof</p>
                              <p className="text-gray-500 text-xs font-mono bg-gray-100 rounded p-2">
                                Hash-chained entry — ID: {p.prediction_id} · registered:{' '}
                                {p.registered_at}
                              </p>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex gap-3 items-center">
            <button
              onClick={handlePrev}
              disabled={offset === 0}
              className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">
              Page {Math.floor(offset / LIMIT) + 1} of {Math.ceil(total / LIMIT)}
            </span>
            <button
              onClick={handleNext}
              disabled={offset + LIMIT >= total}
              className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  );
}
