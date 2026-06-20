import { capabilityLabels } from '@/lib/civilization-api';

export function CivilizationPageShell({
  title,
  eyebrow,
  description,
  children,
}: {
  title: string;
  eyebrow: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-full bg-gray-50 p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6">
          <div className="text-xs font-semibold uppercase tracking-wide text-gray-500">{eyebrow}</div>
          <h1 className="mt-1 text-2xl font-bold text-gray-950">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-gray-600">{description}</p>
        </div>
        <CapabilityLegend />
        <div className="mt-6 space-y-6">{children}</div>
      </div>
    </div>
  );
}

export function CapabilityLegend() {
  return (
    <div className="grid gap-3 md:grid-cols-4">
      {capabilityLabels.map((item) => (
        <div key={item.label} className="rounded-lg border border-gray-200 bg-white p-3">
          <div className="text-sm font-semibold text-gray-900">{item.label}</div>
          <div className="mt-1 text-xs leading-5 text-gray-500">{item.description}</div>
        </div>
      ))}
    </div>
  );
}

export function StatGrid({
  stats,
}: {
  stats: Array<{ label: string; value: string | number; tone?: 'default' | 'good' | 'warn' | 'bad' }>;
}) {
  const toneClass = {
    default: 'text-gray-950',
    good: 'text-green-700',
    warn: 'text-amber-700',
    bad: 'text-red-700',
  };

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {stats.map((stat) => (
        <div key={stat.label} className="rounded-lg border border-gray-200 bg-white p-4">
          <div className={`text-2xl font-bold ${toneClass[stat.tone ?? 'default']}`}>{stat.value}</div>
          <div className="mt-1 text-sm text-gray-500">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}

export function Section({
  title,
  label,
  children,
}: {
  title: string;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
        <h2 className="font-semibold text-gray-900">{title}</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">{label}</span>
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Pill({ children, tone = 'default' }: { children: React.ReactNode; tone?: 'default' | 'good' | 'warn' | 'bad' }) {
  const toneClass = {
    default: 'bg-gray-100 text-gray-700',
    good: 'bg-green-50 text-green-700',
    warn: 'bg-amber-50 text-amber-700',
    bad: 'bg-red-50 text-red-700',
  };

  return <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${toneClass[tone]}`}>{children}</span>;
}
