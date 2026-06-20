import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function CivilizationMapPage() {
  const map = await civilizationApi.getMap();
  const institutions = map.societies.flatMap((society) => society.institutions);
  const departments = institutions.flatMap((institution) => institution.departments);
  const agents = departments.flatMap((department) => department.agents);
  const unresolved = map.societies.reduce((sum, society) => sum + society.unresolvedDisputes, 0);

  return (
    <CivilizationPageShell
      eyebrow="Civilization Map"
      title={map.name}
      description="Operating view across civilization, societies, institutions, departments, and agents with reputation, authority scope, active outputs, disputes, and risk."
    >
      <StatGrid
        stats={[
          { label: 'Constitution', value: map.constitutionVersion },
          { label: 'Societies', value: map.societies.length },
          { label: 'Institutions', value: institutions.length },
          { label: 'Unresolved disputes', value: unresolved, tone: unresolved ? 'warn' : 'good' },
        ]}
      />

      <Section title="Society And Institution Graph" label="Partially Implemented">
        <div className="space-y-5">
          {map.societies.map((society) => (
            <div key={society.id} className="border-l-4 border-gray-300 pl-4">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-semibold text-gray-900">{society.name}</h2>
                <Pill>{society.status}</Pill>
                <Pill tone={society.unresolvedDisputes ? 'warn' : 'good'}>
                  {society.unresolvedDisputes} disputes
                </Pill>
                <span className="text-sm text-gray-500">reputation {society.reputation.toFixed(2)}</span>
              </div>
              <div className="mt-2 text-sm text-gray-600">Authority: {society.authorityScope.join(', ')}</div>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                {society.institutions.map((institution) => (
                  <div key={institution.id} className="rounded-lg border border-gray-200 p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="font-semibold text-gray-900">{institution.name}</div>
                        <div className="text-sm text-gray-500">reputation {institution.reputation.toFixed(2)}</div>
                      </div>
                      <Pill tone={institution.riskLevel === 'high' ? 'warn' : 'default'}>{institution.riskLevel} risk</Pill>
                    </div>
                    <div className="mt-3 text-sm text-gray-600">Authority: {institution.authorityScope.join(', ')}</div>
                    <div className="mt-3 space-y-2">
                      {institution.departments.map((department) => (
                        <div key={department.id} className="rounded-md bg-gray-50 p-3">
                          <div className="flex justify-between gap-3 text-sm">
                            <span className="font-medium text-gray-800">{department.name}</span>
                            <span className="text-gray-500">{department.activeOutputs} outputs</span>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-2">
                            {department.agents.map((agent) => (
                              <Pill key={agent.id}>{agent.id}: {agent.reputation.toFixed(2)}</Pill>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
