'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

const AGENT_IDS = Array.from({ length: 29 }, (_, i) => `agent_${String(i + 1).padStart(3, '0')}`);

interface Memory {
  memory_id: string;
  agent_id: string;
  memory_type: string;
  content: unknown;
  domain: string;
  confidence_score: number;
  created_at: string;
  expires_at: string | null;
}

interface Lesson {
  lesson_id: string;
  agent_id: string;
  lesson: string;
  domain: string;
  created_at: string;
}

export default function MemoryPage() {
  const [agentId, setAgentId] = useState('');
  const [memories, setMemories] = useState<Memory[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!agentId) return;
    setLoading(true);
    setError('');
    Promise.all([
      fetch(`${API}/api/memory/${agentId}`).then(r => r.json()),
      fetch(`${API}/api/memory/lessons`).then(r => r.json()),
    ])
      .then(([memData, lessonData]) => {
        setMemories(memData.memories || memData || []);
        const allLessons: Lesson[] = lessonData.lessons || lessonData || [];
        setLessons(allLessons.filter((l: Lesson) => l.agent_id === agentId));
      })
      .catch(() => setError('Failed to load memory data.'))
      .finally(() => setLoading(false));
  }, [agentId]);

  const episodic = memories.filter(m => m.memory_type === 'episodic').sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  const semantic = memories.filter(m => m.memory_type === 'semantic');

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Agent Memory</h1>
        <p className="text-gray-500 mt-1">Episodic and semantic memory per agent</p>
      </div>

      {/* Memory vs Amnesia explainer */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
        <strong>Memory vs Amnesia:</strong> With memory, an agent starts each task knowing what it learned before.
        Without memory, it starts fresh every time — losing all prior context and lessons.
      </div>

      {/* Agent selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-1">Select Agent</label>
        <select
          value={agentId}
          onChange={e => setAgentId(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white w-64"
        >
          <option value="">— choose an agent —</option>
          {AGENT_IDS.map(id => (
            <option key={id} value={id}>{id}</option>
          ))}
        </select>
      </div>

      {!agentId && (
        <div className="text-center py-12 text-gray-400">Select an agent to view its memory.</div>
      )}

      {agentId && loading && (
        <div className="text-center py-12 text-gray-500">Loading memories...</div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm mb-4">{error}</div>
      )}

      {agentId && !loading && !error && memories.length === 0 && (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200 text-gray-400">
          No memories recorded yet. Run tasks to build episodic memory.
        </div>
      )}

      {agentId && !loading && memories.length > 0 && (
        <div className="space-y-6">
          {/* Episodic */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Episodic Memory ({episodic.length})</h2>
              <p className="text-xs text-gray-400 mt-0.5">Event-based memories ordered by most recent</p>
            </div>
            {episodic.length === 0 ? (
              <div className="px-4 py-6 text-gray-400 text-sm">No episodic memories.</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {episodic.map(m => (
                  <div key={m.memory_id} className="px-4 py-4">
                    <div className="flex items-start justify-between mb-1">
                      <span className="text-xs font-medium text-purple-600 bg-purple-50 px-2 py-0.5 rounded">{m.domain || 'general'}</span>
                      <div className="text-xs text-gray-400">
                        {new Date(m.created_at).toLocaleString()}
                        {m.expires_at && <span className="ml-2 text-orange-400">expires {new Date(m.expires_at).toLocaleDateString()}</span>}
                      </div>
                    </div>
                    <pre className="text-xs bg-gray-50 rounded p-2 mt-2 overflow-auto max-h-32 text-gray-700">
                      {JSON.stringify(m.content, null, 2)}
                    </pre>
                    <div className="text-xs text-gray-400 mt-1">
                      Confidence: <span className={m.confidence_score >= 0.7 ? 'text-green-600' : 'text-orange-500'}>
                        {(m.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Semantic */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Semantic Memory ({semantic.length})</h2>
              <p className="text-xs text-gray-400 mt-0.5">Generalized knowledge and facts</p>
            </div>
            {semantic.length === 0 ? (
              <div className="px-4 py-6 text-gray-400 text-sm">No semantic memories.</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {semantic.map(m => (
                  <div key={m.memory_id} className="px-4 py-4">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">{m.domain || 'general'}</span>
                      <span className="text-xs text-gray-400">
                        Confidence: <span className={m.confidence_score >= 0.7 ? 'text-green-600' : 'text-orange-500'}>
                          {(m.confidence_score * 100).toFixed(0)}%
                        </span>
                      </span>
                    </div>
                    <pre className="text-xs bg-gray-50 rounded p-2 mt-2 overflow-auto max-h-32 text-gray-700">
                      {JSON.stringify(m.content, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Lessons */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Prediction Lessons ({lessons.length})</h2>
              <p className="text-xs text-gray-400 mt-0.5">What this agent has learned from past predictions</p>
            </div>
            {lessons.length === 0 ? (
              <div className="px-4 py-6 text-gray-400 text-sm">No lessons recorded for this agent.</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {lessons.map(l => (
                  <div key={l.lesson_id} className="px-4 py-3">
                    <div className="text-sm text-gray-800">{l.lesson}</div>
                    <div className="text-xs text-gray-400 mt-1">{l.domain} · {new Date(l.created_at).toLocaleDateString()}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
