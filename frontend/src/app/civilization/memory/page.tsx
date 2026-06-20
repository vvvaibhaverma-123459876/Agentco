import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function MemoryDashboardPage() {
  const memory = await civilizationApi.getMemory();
  const precedents = memory.filter((item) => item.type === 'precedent').length;
  const lessons = memory.filter((item) => item.type === 'lesson').length;

  return (
    <CivilizationPageShell
      eyebrow="Memory Dashboard"
      title="Civilizational Memory"
      description="Shows events, lessons, failures, precedents, repeated patterns, and institution history. Memory informs governance but does not directly alter reputation."
    >
      <StatGrid
        stats={[
          { label: 'Memory entries', value: memory.length },
          { label: 'Precedents', value: precedents },
          { label: 'Lessons', value: lessons },
          { label: 'Source-linked', value: memory.length, tone: 'good' },
        ]}
      />

      <Section title="Source-Linked Memory" label="Partially Implemented">
        <div className="divide-y divide-gray-100">
          {memory.map((item) => (
            <div key={item.id} className="grid gap-3 py-4 md:grid-cols-[160px_1fr_240px]">
              <div><Pill>{item.type}</Pill></div>
              <div>
                <div className="font-semibold text-gray-900">{item.title}</div>
                <div className="mt-1 text-sm text-gray-500">Source event: {item.sourceEvent}</div>
              </div>
              <div className="text-sm text-gray-600">{item.affectedEntity}</div>
            </div>
          ))}
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
