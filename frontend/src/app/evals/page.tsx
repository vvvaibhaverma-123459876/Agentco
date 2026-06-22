/**
 * Trustworthiness Benchmarks Dashboard
 * Main page for viewing benchmark runs and leaderboards
 */
'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface BenchmarkRun {
  run_id: string;
  benchmark_id: string;
  created_at: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  models: string[];
  n_cases: number;
}

interface LeaderboardEntry {
  rank: number;
  model_id: string;
  overall_score: number;
  decision_accuracy: number;
  hallucination_rate: number;
  evidence_f1: number;
}

export default function EvalsPage() {
  const [runs, setRuns] = useState<BenchmarkRun[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);

  useEffect(() => {
    fetchRuns();
  }, []);

  useEffect(() => {
    if (selectedRun) {
      fetchLeaderboard(selectedRun);
    }
  }, [selectedRun]);

  async function fetchRuns() {
    try {
      const res = await fetch('/api/evals/runs?limit=50');
      const data = await res.json();
      setRuns(data.data?.runs || []);
      if (data.data?.runs?.length > 0) {
        setSelectedRun(data.data.runs[0].run_id);
      }
    } catch (err) {
      console.error('Failed to fetch runs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function fetchLeaderboard(run_id: string) {
    try {
      const res = await fetch(`/api/evals/runs/${run_id}`);
      const data = await res.json();
      if (data.data?.models) {
        const sorted = data.data.models.sort(
          (a: any, b: any) => b.overall_score - a.overall_score
        );
        setLeaderboard(
          sorted.map((m: any, i: number) => ({
            rank: i + 1,
            model_id: m.model_id,
            overall_score: m.overall_score,
            decision_accuracy: m.decision_accuracy,
            hallucination_rate: m.hallucination_rate,
            evidence_f1: m.evidence_f1,
          }))
        );
      }
    } catch (err) {
      console.error('Failed to fetch leaderboard:', err);
    }
  }

  function getStatusBadge(status: string) {
    const colors: Record<string, string> = {
      completed: 'bg-green-100 text-green-800',
      running: 'bg-blue-100 text-blue-800',
      pending: 'bg-yellow-100 text-yellow-800',
      failed: 'bg-red-100 text-red-800',
    };
    return (
      <span className={`px-2 py-1 rounded text-sm font-medium ${colors[status] || colors.pending}`}>
        {status}
      </span>
    );
  }

  if (loading) {
    return <div className="p-8">Loading...</div>;
  }

  return (
    <div className="max-w-7xl mx-auto p-8">
      <h1 className="text-4xl font-bold mb-2">Trustworthiness Benchmarks</h1>
      <p className="text-gray-600 mb-8">
        Measure and compare LLM trustworthiness on high-stakes problems
      </p>

      {/* Run History */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          <h2 className="text-2xl font-semibold mb-4">Recent Runs</h2>
          <div className="space-y-2">
            {runs.length === 0 ? (
              <p className="text-gray-500">No runs yet. Run a benchmark to get started.</p>
            ) : (
              runs.map(run => (
                <button
                  key={run.run_id}
                  onClick={() => setSelectedRun(run.run_id)}
                  className={`w-full p-3 text-left rounded border-2 transition-colors ${
                    selectedRun === run.run_id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium text-sm truncate">
                    {run.benchmark_id}
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(run.created_at).toLocaleDateString()}
                  </div>
                  <div className="mt-1">
                    {getStatusBadge(run.status)}
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="mt-6 pt-6 border-t">
            <Link
              href="/evals/run-benchmark"
              className="block w-full py-2 px-4 bg-blue-600 text-white rounded text-center font-medium hover:bg-blue-700"
            >
              + New Benchmark Run
            </Link>
          </div>
        </div>

        {/* Leaderboard */}
        <div className="lg:col-span-2">
          <h2 className="text-2xl font-semibold mb-4">Leaderboard</h2>

          {leaderboard.length === 0 ? (
            <p className="text-gray-500">No results yet. Select a run or start a new one.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-100 border-b-2 border-gray-300">
                  <tr>
                    <th className="px-4 py-2 text-left">Rank</th>
                    <th className="px-4 py-2 text-left">Model</th>
                    <th className="px-4 py-2 text-right">Overall</th>
                    <th className="px-4 py-2 text-right">Decision</th>
                    <th className="px-4 py-2 text-right">Hallucination</th>
                    <th className="px-4 py-2 text-right">Evidence F1</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map(entry => (
                    <tr key={entry.model_id} className="border-b hover:bg-gray-50">
                      <td className="px-4 py-2 font-semibold">{entry.rank}</td>
                      <td className="px-4 py-2">
                        <Link
                          href={`/evals/${selectedRun}/${entry.model_id}`}
                          className="text-blue-600 hover:underline"
                        >
                          {entry.model_id}
                        </Link>
                      </td>
                      <td className="px-4 py-2 text-right font-medium">
                        {entry.overall_score.toFixed(3)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {(entry.decision_accuracy * 100).toFixed(1)}%
                      </td>
                      <td className="px-4 py-2 text-right">
                        <span
                          className={`${
                            entry.hallucination_rate > 0.1
                              ? 'text-red-600 font-medium'
                              : 'text-green-600'
                          }`}
                        >
                          {(entry.hallucination_rate * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right">
                        {entry.evidence_f1.toFixed(3)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Metrics Legend */}
      <div className="mt-12 p-6 bg-gray-50 rounded-lg border border-gray-200">
        <h3 className="font-semibold mb-3">Metrics Explained</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <strong>Overall Score:</strong> Composite trustworthiness metric (0-1, higher better)
          </div>
          <div>
            <strong>Decision Accuracy:</strong> Approval/rejection/escalation correctness
          </div>
          <div>
            <strong>Hallucination Rate:</strong> Unsupported or false claims (0-1, lower better)
          </div>
          <div>
            <strong>Evidence F1:</strong> Precision and recall of cited evidence sources
          </div>
        </div>
      </div>
    </div>
  );
}
