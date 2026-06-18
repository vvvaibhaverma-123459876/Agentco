'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

interface Stats {
  predictions_total: number;
  predictions_resolved_true: number;
  predictions_resolved_false: number;
  predictions_pending: number;
  agents_active: number;
  events_last_hour: number;
}

interface AgentEvent {
  event_id: string;
  event_type: string;
  producer_agent_id: string;
  timestamp: string;
  confidence_score?: number;
}

function StatusDot({ healthy }: { healthy: boolean | null }) {
  if (healthy === null)
    return <span className="w-3 h-3 rounded-full bg-gray-300 inline-block" />;
  return (
    <span
      className={`w-3 h-3 rounded-full inline-block ${healthy ? 'bg-green-500' : 'bg-red-500'}`}
    />
  );
}

export default function HomePage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [eventsError, setEventsError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  async function loadData() {
    try {
      const s = await apiFetch<Stats>('/api/stats');
      setStats(s);
      setError(null);
    } catch {
      setError('Could not load stats — is the backend running?');
    }
    try {
      const ev = await apiFetch<{ events: AgentEvent[] }>('/api/events/recent?limit=10');
      setEvents(ev.events ?? []);
      setEventsError(null);
    } catch {
      setEventsError('Could not load events — is the backend running?');
    }
    setLastRefresh(new Date());
  }

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const statCards = stats
    ? [
        { label: 'Total Predictions', value: stats.predictions_total, color: 'text-blue-600' },
        { label: 'Resolved True', value: stats.predictions_resolved_true, color: 'text-green-600' },
        { label: 'Resolved False', value: stats.predictions_resolved_false, color: 'text-red-600' },
        { label: 'Pending', value: stats.predictions_pending, color: 'text-yellow-600' },
        { label: 'Active Agents', value: stats.agents_active, color: 'text-purple-600' },
        { label: 'Events Last Hour', value: stats.events_last_hour, color: 'text-indigo-600' },
      ]
    : [];

  const services = [
    { name: 'Postgres', healthy: stats !== null },
    { name: 'Kafka', healthy: stats !== null ? stats.events_last_hour >= 0 : null },
    { name: 'Redis', healthy: stats !== null ? stats.agents_active >= 0 : null },
    { name: 'Ollama', healthy: stats !== null ? stats.agents_active > 0 : null },
  ];

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Tagline */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">AgentCo Live Overview</h1>
        <p className="text-gray-500 text-base italic">
          AgentCo makes AI earn the right to be believed — by predicting before it knows, and letting
          reality be the judge.
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Last refreshed: {lastRefresh.toLocaleTimeString()} · Auto-refreshes every 30s
        </p>
      </div>

      {/* Stat Cards */}
      {error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {error}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          {stats === null
            ? Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse"
                >
                  <div className="h-4 bg-gray-200 rounded w-2/3 mb-2" />
                  <div className="h-8 bg-gray-200 rounded w-1/3" />
                </div>
              ))
            : statCards.map((card) => (
                <div key={card.label} className="bg-white rounded-lg border border-gray-200 p-4">
                  <p className="text-sm text-gray-500 mb-1">{card.label}</p>
                  <p className={`text-3xl font-bold ${card.color}`}>
                    {card.value.toLocaleString()}
                  </p>
                </div>
              ))}
        </div>
      )}

      {/* System Health Strip */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">System Health</h2>
        <div className="flex gap-6 flex-wrap">
          {services.map((svc) => (
            <div key={svc.name} className="flex items-center gap-2">
              <StatusDot healthy={svc.healthy} />
              <span className="text-sm text-gray-600">{svc.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Live Event Feed */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Live Event Feed (last 10)</h2>
        {eventsError ? (
          <p className="text-red-600 text-sm">{eventsError}</p>
        ) : events.length === 0 ? (
          <p className="text-gray-400 text-sm">No events yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-100">
                  <th className="pb-2 pr-4 font-medium">Type</th>
                  <th className="pb-2 pr-4 font-medium">Producer</th>
                  <th className="pb-2 pr-4 font-medium">Confidence</th>
                  <th className="pb-2 font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.event_id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 pr-4 font-mono text-xs text-blue-700">{ev.event_type}</td>
                    <td className="py-2 pr-4 text-gray-600 text-xs">{ev.producer_agent_id}</td>
                    <td className="py-2 pr-4 text-gray-600">
                      {ev.confidence_score != null
                        ? `${(ev.confidence_score * 100).toFixed(0)}%`
                        : '—'}
                    </td>
                    <td className="py-2 text-gray-400 text-xs">
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* CTA Buttons */}
      <div className="flex gap-4">
        <Link
          href="/ledger"
          className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          View Prediction Ledger
        </Link>
        <Link
          href="/dashboard"
          className="bg-white text-gray-700 border border-gray-300 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
        >
          View Agent Dashboard
        </Link>
      </div>
    </div>
  );
}
