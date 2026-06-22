export default function GovernancePage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Governance Console</h1>
      <p className="text-gray-500 mt-1">Inspect policy, evidence, attestation, and why-allowed chains for actions.</p>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {[
          ['Policy Gates', 'High and critical risk actions require approval.'],
          ['Action Attestations', 'Consequential actions carry hashes, signatures, and transparency references.'],
          ['Evidence Labels', 'Validation surfaces distinguish EXTERNAL-VALIDATED, REAL, FIXTURE, simulated, and unresolved.'],
        ].map(([title, body]) => (
          <div key={title} className="rounded-lg border border-gray-200 bg-white p-4">
            <h2 className="font-semibold text-gray-900">{title}</h2>
            <p className="mt-2 text-sm text-gray-500">{body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
