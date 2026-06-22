'use client';

import { useEffect, useState } from 'react';
import {
  getAutonomyDashboard,
  listAutonomyRuns,
  healthCheck,
  type AutonomyRun,
} from '@/lib/api/autonomy';

export default function AutonomyDashboard() {
  const [runs, setRuns] = useState<AutonomyRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiAvailable, setApiAvailable] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setError(null);

        // Check if API is available
        const isAvailable = await healthCheck();
        setApiAvailable(isAvailable);

        if (isAvailable) {
          // Load recent runs
          const recentRuns = await listAutonomyRuns(10);
          setRuns(recentRuns);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        setRuns([]);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Autonomy Dashboard</h1>
        <div className="text-gray-500">Loading autonomy data...</div>
      </div>
    );
  }

  if (!apiAvailable) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-8">Autonomy Dashboard</h1>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-yellow-800">
          ⚠️ Backend API not available. Ensure the server is running with DATABASE_URL set.
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8">Autonomy Dashboard</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-800 mb-6">
          ❌ {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="text-gray-600 text-sm">Total Runs</div>
          <div className="text-3xl font-bold text-blue-600">{runs.length}</div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="text-gray-600 text-sm">Completed</div>
          <div className="text-3xl font-bold text-green-600">
            {runs.filter((r) => r.status === 'completed').length}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="text-gray-600 text-sm">Failed</div>
          <div className="text-3xl font-bold text-red-600">
            {runs.filter((r) => r.status === 'failed').length}
          </div>
        </div>
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="text-gray-600 text-sm">Promotion Eligible</div>
          <div className="text-3xl font-bold text-purple-600">
            {runs.filter((r) => r.promotionEligible).length}
          </div>
        </div>
      </div>

      {/* Recent Runs Table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Recent Autonomy Runs</h2>
        </div>

        {runs.length === 0 ? (
          <div className="px-6 py-8 text-gray-500 text-center">
            No autonomy runs found. Execute: <code className="bg-gray-100 px-2 py-1 rounded">make autonomy-level3-smoke</code>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Run ID</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Trace ID</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Task</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Promotion</th>
                  <th className="px-6 py-3 text-left text-sm font-medium text-gray-700">Started</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-6 py-3 text-sm font-mono text-blue-600">{run.runId.substring(0, 12)}...</td>
                    <td className="px-6 py-3 text-sm">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                          run.status === 'completed'
                            ? 'bg-green-100 text-green-800'
                            : run.status === 'failed'
                              ? 'bg-red-100 text-red-800'
                              : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-sm font-mono">{run.traceId.substring(0, 8)}...</td>
                    <td className="px-6 py-3 text-sm font-mono">{run.taskId ? run.taskId.substring(0, 8) : '-'}...</td>
                    <td className="px-6 py-3 text-sm">
                      <span
                        className={`inline-block px-3 py-1 rounded-full text-xs font-medium ${
                          run.promotionEligible
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {run.promotionEligible ? 'Eligible' : 'Blocked'}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-sm text-gray-600">
                      {new Date(run.startedAt).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Section */}
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="font-semibold text-blue-900 mb-3">LEVEL_3 Autonomy Implementation</h3>
        <ul className="text-sm text-blue-800 space-y-2">
          <li>✅ Backend services: learner, eval-harness, self-modification-validator, orchestrator</li>
          <li>✅ Database schemas: 15 migrations (021-035) with full autonomy infrastructure</li>
          <li>✅ End-to-end loop: perception → plan → execution → memory → eval → promotion</li>
          <li>✅ Safety gates: eval harness blocks promotion if thresholds not met</li>
          <li>✅ Rollback testing: canary deployment with rollback on regression</li>
          <li>📊 To run smoke test: <code className="bg-blue-100 px-2 py-1 rounded">DATABASE_URL='postgresql://...' make autonomy-level3-smoke</code></li>
        </ul>
      </div>
    </div>
  );
}
