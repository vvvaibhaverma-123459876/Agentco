import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function CalibrationDashboardPage() {
  const claims = await civilizationApi.getCalibration();
  const accepted = claims.filter((claim) => claim.independenceStatus === 'accepted').length;
  const rejected = claims.filter((claim) => claim.independenceStatus === 'rejected').length;

  return (
    <CivilizationPageShell
      eyebrow="Calibration Dashboard"
      title="Epistemic Reserve"
      description="Displays claims, source lineage, resolution independence status, trust scores, recomputable credentials, and audit packages."
    >
      <StatGrid
        stats={[
          { label: 'Claims', value: claims.length },
          { label: 'Accepted independent resolutions', value: accepted, tone: 'good' },
          { label: 'Rejected circular resolutions', value: rejected, tone: rejected ? 'bad' : 'good' },
          { label: 'Credentials issued', value: claims.filter((claim) => claim.credentialStatus.includes('issued')).length },
        ]}
      />

      <Section title="Claim Independence Ledger" label="Shipped">
        <div className="space-y-4">
          {claims.map((claim) => (
            <div key={claim.id} className="rounded-lg border border-gray-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-gray-900">{claim.claim}</div>
                  <div className="mt-1 text-sm text-gray-500">{claim.id}</div>
                </div>
                <Pill tone={claim.independenceStatus === 'accepted' ? 'good' : claim.independenceStatus === 'rejected' ? 'bad' : 'warn'}>
                  {claim.independenceStatus}
                </Pill>
              </div>
              <div className="mt-4 grid gap-3 text-sm md:grid-cols-2">
                <div className="rounded-md bg-gray-50 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Claim source</div>
                  <div className="mt-1 break-words text-gray-700">{claim.claimSource}</div>
                </div>
                <div className="rounded-md bg-gray-50 p-3">
                  <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Resolution source</div>
                  <div className="mt-1 break-words text-gray-700">{claim.resolutionSource}</div>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Pill>trust {claim.trustScore.toFixed(2)}</Pill>
                <Pill>{claim.credentialStatus}</Pill>
                <Pill>{claim.auditPackage}</Pill>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
