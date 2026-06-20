import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function GovernanceDashboardPage() {
  const decisions = await civilizationApi.getGovernance();
  const blocked = decisions.filter((decision) => decision.selfAuthorityCheck === 'blocked').length;

  return (
    <CivilizationPageShell
      eyebrow="Governance Dashboard"
      title="Governed Decisions"
      description="Shows proposed decisions, approvers, affected entities, self-authority checks, audit trails, and rollback availability."
    >
      <StatGrid
        stats={[
          { label: 'Decisions', value: decisions.length },
          { label: 'Self-authority blocked', value: blocked, tone: blocked ? 'bad' : 'good' },
          { label: 'Rollback-capable', value: decisions.filter((decision) => decision.rollbackAvailable).length },
          { label: 'Mutation path', value: 'governed API' },
        ]}
      />

      <Section title="Decision Ledger" label="Partially Implemented">
        <div className="grid gap-4 lg:grid-cols-2">
          {decisions.map((decision) => (
            <div key={decision.id} className="rounded-lg border border-gray-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-semibold text-gray-900">{decision.proposal}</div>
                  <div className="mt-1 text-sm text-gray-500">Affected: {decision.affectedEntity}</div>
                </div>
                <Pill tone={decision.selfAuthorityCheck === 'blocked' ? 'bad' : 'good'}>
                  self-authority {decision.selfAuthorityCheck}
                </Pill>
              </div>
              <div className="mt-3 text-sm text-gray-700">Approver: {decision.approver}</div>
              <div className="mt-4">
                <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">Audit trail</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {decision.auditTrail.map((event) => <Pill key={event}>{event}</Pill>)}
                </div>
              </div>
              <div className="mt-4">
                <Pill tone={decision.rollbackAvailable ? 'warn' : 'default'}>
                  rollback {decision.rollbackAvailable ? 'available' : 'not available'}
                </Pill>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
