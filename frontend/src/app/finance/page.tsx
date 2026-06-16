'use client';

export default function FinancePage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Financial Dashboard</h1>
      <p className="text-gray-500 mt-1">P&L, burn rate, runway — read-only feed from CFO-Agent</p>
      <div className="mt-6 grid grid-cols-3 gap-4">
        {['Monthly Recurring Revenue', 'Burn Rate', 'Runway', 'Compute Budget Used', 'YTD Revenue', 'Open Spend Approvals'].map(label => (
          <div key={label} className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="text-sm text-gray-500">{label}</div>
            <div className="text-2xl font-bold mt-1 text-gray-300">—</div>
            <div className="text-xs text-gray-400 mt-1">Connect CFO-Agent</div>
          </div>
        ))}
      </div>
    </div>
  );
}
