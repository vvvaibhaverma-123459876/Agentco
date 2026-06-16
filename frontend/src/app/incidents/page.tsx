'use client';

export default function IncidentsPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Incident Log</h1>
      <p className="text-gray-500 mt-1">All incidents with timeline, rollback status, and postmortem links</p>
      <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800">
        ✓ No active incidents
      </div>
      <div className="mt-4 bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-gray-400 text-sm text-center py-8">
          Incidents appear here when DevOps-Agent fires engineering.incident.detected events.
          Auto-rollback threshold: error rate &gt; 5% in 5 minutes.
        </p>
      </div>
    </div>
  );
}
