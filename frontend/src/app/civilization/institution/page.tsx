import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function InstitutionDashboardPage() {
  const institution = await civilizationApi.getInstitution();
  const agents = institution.departments.flatMap((department) => department.agents);

  return (
    <CivilizationPageShell
      eyebrow="Institution Dashboard"
      title={institution.name}
      description="Institution operating view for contract, departments, members, outputs, reviews, failures, reputation history, authority scope, and restrictions."
    >
      <StatGrid
        stats={[
          { label: 'Status', value: institution.status },
          { label: 'Departments', value: institution.departments.length },
          { label: 'Members', value: agents.length },
          { label: 'Restrictions', value: institution.restrictions.length, tone: institution.restrictions.length ? 'warn' : 'good' },
        ]}
      />

      <Section title="Contract And Authority" label="Shipped">
        <p className="text-sm text-gray-700">{institution.contract}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {institution.authorityScope.map((scope) => <Pill key={scope}>{scope}</Pill>)}
        </div>
        <div className="mt-4 space-y-2">
          {institution.restrictions.map((restriction) => (
            <div key={restriction} className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">{restriction}</div>
          ))}
        </div>
      </Section>

      <Section title="Departments And Members" label="Partially Implemented">
        <div className="grid gap-4 lg:grid-cols-2">
          {institution.departments.map((department) => (
            <div key={department.id} className="rounded-lg border border-gray-200 p-4">
              <div className="flex justify-between gap-3">
                <div>
                  <div className="font-semibold text-gray-900">{department.name}</div>
                  <div className="text-sm text-gray-500">reputation {department.reputation.toFixed(2)}</div>
                </div>
                <Pill>{department.activeOutputs} outputs</Pill>
              </div>
              <div className="mt-3 divide-y divide-gray-100">
                {department.agents.map((agent) => (
                  <div key={agent.id} className="flex items-center justify-between py-2 text-sm">
                    <span className="font-medium text-gray-800">{agent.id}</span>
                    <span className="text-gray-500">{agent.role} · {agent.reputation.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Outputs, Reviews, Failures" label="Shipped">
        <div className="grid gap-4 lg:grid-cols-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Outputs</h3>
            <div className="mt-2 space-y-2">
              {institution.outputs.map((output) => (
                <div key={output.id} className="rounded-md bg-gray-50 p-3 text-sm">
                  <div className="font-medium text-gray-900">{output.title}</div>
                  <div className="mt-1 text-gray-500">{output.status} · {output.risk} risk</div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Reviews</h3>
            <div className="mt-2 space-y-2">
              {institution.reviews.map((review) => (
                <div key={review.id} className="rounded-md bg-gray-50 p-3 text-sm">
                  <div className="font-medium text-gray-900">{review.reviewerInstitution}</div>
                  <div className="mt-1 text-gray-500">{review.finalDecision} · {review.challengeStatus}</div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Failures</h3>
            <div className="mt-2 space-y-2">
              {institution.failures.map((failure) => (
                <div key={failure.id} className="rounded-md bg-gray-50 p-3 text-sm">
                  <div className="font-medium text-gray-900">{failure.summary}</div>
                  <div className="mt-1 text-gray-500">{failure.status}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
