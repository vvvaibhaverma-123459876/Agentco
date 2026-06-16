'use client';

export default function PerformancePage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Performance Dashboard</h1>
      <p className="text-gray-500 mt-1">Per-agent accuracy, latency, cost-per-task — powered by Performance-Agent</p>
      <div className="mt-6 grid grid-cols-3 gap-4">
        {[
          { label: 'Avg Task Latency', value: '< 30s', status: 'ok' },
          { label: 'Agent Error Rate', value: '< 1%', status: 'ok' },
          { label: 'Audit Coverage', value: '100%', status: 'ok' },
          { label: 'Override Queue SLA', value: '< 4h avg', status: 'ok' },
          { label: 'Confidence Calibration Error', value: '< 0.1', status: 'ok' },
          { label: 'Missed Escalation Rate', value: '0%', status: 'ok' },
        ].map(({ label, value, status }) => (
          <div key={label} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-sm text-gray-500">{label}</div>
            <div className="text-2xl font-bold mt-1 text-green-600">{value}</div>
            <div className="text-xs text-gray-400 mt-1">Within threshold</div>
          </div>
        ))}
      </div>
      <div className="mt-6 bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-gray-400 text-sm text-center py-8">
          Connect OpenTelemetry to populate per-agent latency, cost, and accuracy charts.
        </p>
      </div>
    </div>
  );
}
