'use client';

import { useEffect, useRef, useState } from 'react';
import { AgentEvent, RISK_COLORS } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? 'ws://localhost:3001/ws/events';
const MAX_EVENTS = 200;

export default function EventsPage() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [filter, setFilter] = useState('');
  const [paused, setPaused] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => { setConnected(false); setTimeout(connect, 3000); };
      ws.onmessage = (e) => {
        if (paused) return;
        try {
          const event = JSON.parse(e.data);
          if (event.event_id) {
            setEvents(prev => [event, ...prev].slice(0, MAX_EVENTS));
          }
        } catch {}
      };
    };
    connect();
    return () => wsRef.current?.close();
  }, [paused]);

  const filtered = filter ? events.filter(e => e.event_type.includes(filter) || e.producer_agent_id.includes(filter)) : events;

  return (
    <div className="p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Event Stream</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-gray-500 text-sm">{connected ? 'Live' : 'Reconnecting...'}</span>
          </div>
        </div>
        <div className="flex gap-3">
          <input placeholder="Filter events..." value={filter} onChange={e => setFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-1.5 text-sm w-48" />
          <button onClick={() => setPaused(p => !p)}
            className={`px-3 py-1.5 text-sm rounded-md border ${paused ? 'bg-yellow-50 border-yellow-300 text-yellow-700' : 'border-gray-300 hover:bg-gray-50'}`}>
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button onClick={() => setEvents([])} className="px-3 py-1.5 text-sm rounded-md border border-gray-300 hover:bg-gray-50">
            Clear
          </button>
        </div>
      </div>

      <div className="space-y-2 font-mono text-xs">
        {filtered.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Waiting for events...</div>
        ) : filtered.map(event => (
          <div key={event.event_id} className="bg-white rounded border border-gray-200 px-3 py-2 flex items-start gap-3">
            <span className="text-gray-400 shrink-0">{new Date(event.timestamp).toLocaleTimeString()}</span>
            <span className={`px-1.5 py-0.5 rounded text-xs shrink-0 ${RISK_COLORS[event.risk_level]}`}>{event.risk_level}</span>
            <span className="text-blue-600 shrink-0">{event.producer_agent_id}</span>
            <span className="text-gray-700 font-semibold shrink-0">{event.event_type}</span>
            <span className="text-green-600 shrink-0">{(event.confidence_score * 100).toFixed(0)}%</span>
            <span className="text-gray-400 truncate">{JSON.stringify(event.payload)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
