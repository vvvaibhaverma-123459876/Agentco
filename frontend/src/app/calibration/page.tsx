'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

interface TrustScore {
  agent_id: string;
  domain: string;
  horizon_class: string;
  trust_factor: number;
  n_resolved: number;
  n_predictions: number;
  brier_mean?: number;
  log_mean?: number;
  computed_at: string;
}

interface CalibrationPoint {
  stated_confidence: number;
  actual_accuracy: number;
  n: number;
}

function TrustColor(tf: number) {
  if (tf >= 0.8) return 'text-green-600';
  if (tf >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
}

function CalibrationChart({ points }: { points: CalibrationPoint[] }) {
  if (points.length === 0)
    return (
      <p className="text-gray-400 text-sm">No resolved predictions yet for this agent.</p>
    );

  const W = 300;
  const H = 300;
  const PAD = 30;

  const toX = (v: number) => PAD + v * (W - 2 * PAD);
  const toY = (v: number) => H - PAD - v * (H - 2 * PAD);

  const polyline = points
    .slice()
    .sort((a, b) => a.stated_confidence - b.stated_confidence)
    .map((p) => `${toX(p.stated_confidence)},${toY(p.actual_accuracy)}`)
    .join(' ');

  return (
    <svg width={W} height={H} className="border border-gray-100 rounded bg-gray-50">
      {/* Grid */}
      {[0, 0.25, 0.5, 0.75, 1].map((v) => (
        <g key={v}>
          <line
            x1={toX(v)}
            y1={PAD}
            x2={toX(v)}
            y2={H - PAD}
            stroke="#e5e7eb"
            strokeWidth={1}
          />
          <line
            x1={PAD}
            y1={toY(v)}
            x2={W - PAD}
            y2={toY(v)}
            stroke="#e5e7eb"
            strokeWidth={1}
          />
          <text x={toX(v)} y={H - 8} textAnchor="middle" fontSize={9} fill="#9ca3af">
            {v}
          </text>
          <text x={10} y={toY(v) + 3} textAnchor="middle" fontSize={9} fill="#9ca3af">
            {v}
          </text>
        </g>
      ))}
      {/* Diagonal reference */}
      <line
        x1={toX(0)}
        y1={toY(0)}
        x2={toX(1)}
        y2={toY(1)}
        stroke="#d1d5db"
        strokeWidth={1}
        strokeDasharray="4,3"
      />
      {/* Actual calibration line */}
      <polyline points={polyline} fill="none" stroke="#3b82f6" strokeWidth={2} />
      {/* Points */}
      {points.map((p, i) => (
        <circle
          key={i}
          cx={toX(p.stated_confidence)}
          cy={toY(p.actual_accuracy)}
          r={4}
          fill="#3b82f6"
        >
          <title>
            Stated: {(p.stated_confidence * 100).toFixed(0)}% | Actual:{' '}
            {(p.actual_accuracy * 100).toFixed(0)}% | n={p.n}
          </title>
        </circle>
      ))}
      {/* Axis labels */}
      <text x={W / 2} y={H - 1} textAnchor="middle" fontSize={10} fill="#6b7280">
        Stated Confidence
      </text>
      <text
        x={10}
        y={H / 2}
        textAnchor="middle"
        fontSize={10}
        fill="#6b7280"
        transform={`rotate(-90,10,${H / 2})`}
      >
        Actual Accuracy
      </text>
    </svg>
  );
}

export default function CalibrationPage() {
  const [trustScores, setTrustScores] = useState<TrustScore[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [curvePoints, setCurvePoints] = useState<CalibrationPoint[]>([]);
  const [curveLoading, setCurveLoading] = useState(false);
  const [curveError, setCurveError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<{ trust_scores: TrustScore[] }>('/api/trust-scores');
        setTrustScores(data.trust_scores ?? []);
        if ((data.trust_scores ?? []).length > 0) {
          setSelectedAgent(data.trust_scores[0].agent_id);
        }
      } catch {
        setError('Could not load trust scores — is the backend running?');
      }
    })();
  }, []);

  useEffect(() => {
    if (!selectedAgent) return;
    setCurveLoading(true);
    setCurveError(null);
    (async () => {
      try {
        const data = await apiFetch<{ points: CalibrationPoint[] }>(
          `/api/trust-scores/calibration-curve/${selectedAgent}`
        );
        setCurvePoints(data.points ?? []);
      } catch {
        setCurveError('Could not load calibration curve — is the backend running?');
        setCurvePoints([]);
      } finally {
        setCurveLoading(false);
      }
    })();
  }, [selectedAgent]);

  // Group by agent_id
  const grouped: Record<string, TrustScore[]> = {};
  for (const ts of trustScores) {
    if (!grouped[ts.agent_id]) grouped[ts.agent_id] = [];
    grouped[ts.agent_id].push(ts);
  }
  const agentIds = Object.keys(grouped);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Calibration & Trust Scores</h1>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-800">
          An agent with trust_factor=0.85 has been right 85% of the time when it expressed this
          level of confidence. This number is earned, not assigned.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {error}
        </div>
      )}

      {!error && agentIds.length === 0 && (
        <p className="text-gray-400 text-sm">No trust scores available yet.</p>
      )}

      {/* Per-agent cards */}
      <div className="space-y-4 mb-8">
        {agentIds.map((agentId) => {
          const rows = grouped[agentId];
          const topTf = rows[0]?.trust_factor ?? 0;
          return (
            <div key={agentId} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-base font-semibold text-gray-800">{agentId}</h2>
                <span className={`text-2xl font-bold ${TrustColor(topTf)}`}>
                  {(topTf * 100).toFixed(1)}%
                </span>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-100">
                    <th className="pb-1 pr-4 font-medium">Domain</th>
                    <th className="pb-1 pr-4 font-medium">Horizon</th>
                    <th className="pb-1 pr-4 font-medium">Trust</th>
                    <th className="pb-1 pr-4 font-medium">Resolved / Total</th>
                    <th className="pb-1 pr-4 font-medium">Brier</th>
                    <th className="pb-1 font-medium">Log</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-b border-gray-50">
                      <td className="py-1 pr-4 text-gray-700">{r.domain}</td>
                      <td className="py-1 pr-4 text-gray-500 text-xs">{r.horizon_class}</td>
                      <td className={`py-1 pr-4 font-semibold ${TrustColor(r.trust_factor)}`}>
                        {(r.trust_factor * 100).toFixed(1)}%
                      </td>
                      <td className="py-1 pr-4 text-gray-600">
                        {r.n_resolved} / {r.n_predictions}
                      </td>
                      <td className="py-1 pr-4 text-gray-500">
                        {r.brier_mean != null ? r.brier_mean.toFixed(4) : '—'}
                      </td>
                      <td className="py-1 text-gray-500">
                        {r.log_mean != null ? r.log_mean.toFixed(4) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-gray-400 mt-2">
                Computed: {new Date(rows[0].computed_at).toLocaleString()}
              </p>
            </div>
          );
        })}
      </div>

      {/* Calibration Curve */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h2 className="text-base font-semibold text-gray-800 mb-3">Calibration Curve</h2>
        <div className="flex items-center gap-3 mb-4">
          <label className="text-sm text-gray-600">Agent:</label>
          <select
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {agentIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </div>
        {curveError ? (
          <p className="text-red-600 text-sm">{curveError}</p>
        ) : curveLoading ? (
          <p className="text-gray-400 text-sm">Loading curve…</p>
        ) : (
          <CalibrationChart points={curvePoints} />
        )}
        <p className="text-xs text-gray-400 mt-2">
          Diagonal = perfect calibration. Points above the line = overconfident; below = underconfident.
        </p>
      </div>
    </div>
  );
}
