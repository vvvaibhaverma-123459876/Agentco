'use client';

import { useCallback, useEffect, useState } from 'react';

/**
 * Civilization operator console (build phase C13).
 *
 * Every value on this page comes from the governed backend through the
 * server-side API proxy (which injects the service credential); there is no
 * fabricated data. Protected actions (kill switch, emergency stop) require an
 * explicit confirmation and a reason before they are sent.
 */

interface Overview {
  bootstrapped: boolean;
  civilization: null | {
    id: string; name: string; status: string;
    active_charter_version: number | null; protected_invariants: number; active_emergencies: number;
    objectives_by_status: Record<string, number>;
  };
  topology?: { societies: Array<{ id: string; name: string; status: string; citizen_members: number; institutions: number; jurisdictions: string[] }>; civilization_wide_institutions: Array<{ institution_id: string; jurisdiction_keys: string[] }> };
  status?: Record<string, number | string>;
  open_work?: Record<string, Array<{ id: string; title?: string; dispute_type?: string; status: string }>>;
  recent_events?: Array<{ event_type: string; object_type: string | null; occurred_at: string }>;
  recent_ticks?: Array<{ tick_number: number; mode: string; work_routed: number; created_at: string }>;
  generated_at?: string;
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { accept: 'application/json' } });
  if (!res.ok) throw new Error(`request failed: ${res.status}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`request failed: ${res.status}`);
  return res.json() as Promise<T>;
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="mt-1 text-xs uppercase tracking-wide text-gray-500">{label}</div>
    </div>
  );
}

export default function CivilizationOperatorPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    setError(null);
    getJson<Overview>('/api/civilization/operator/overview')
      .then(setOverview)
      .catch((e) => setError(e instanceof Error ? e.message : 'failed to load'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [load]);

  const runTick = useCallback(async () => {
    setBusy(true);
    try { await postJson('/api/civilization/os/tick', {}); load(); }
    catch (e) { setError(e instanceof Error ? e.message : 'tick failed'); }
    finally { setBusy(false); }
  }, [load]);

  const engageKillSwitch = useCallback(async () => {
    const reason = window.prompt('Engaging the civilization kill switch stops all protected work.\nEnter a reason to confirm:');
    if (!reason) return;
    setBusy(true);
    try {
      // The kill switch is engaged through an authorized governance emergency power.
      await postJson('/api/civilization/governance/emergency-powers', {
        scope: 'operator-console', power: 'halt_protected_work', reason,
        authorized_decision_ref: 'operator-console-confirmation', ttl_seconds: 3600,
        engage_kill_switch: true, actor_id: 'operator-console',
      });
      load();
    } catch (e) { setError(e instanceof Error ? e.message : 'kill switch failed'); }
    finally { setBusy(false); }
  }, [load]);

  if (loading) return <div className="p-6 text-gray-500">Loading civilization state…</div>;

  if (error && !overview) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900">Civilization</h1>
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load civilization state: {error}
        </div>
      </div>
    );
  }

  if (!overview?.bootstrapped || !overview.civilization) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900">Civilization</h1>
        <p className="mt-2 text-gray-500">No active civilization root. Bootstrap the kernel to begin.</p>
      </div>
    );
  }

  const civ = overview.civilization;
  const status = overview.status ?? {};

  return (
    <div className="p-6">
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{civ.name}</h1>
          <p className="mt-1 text-gray-500">
            Civilization <span className="font-mono text-xs">{civ.id}</span> · status{' '}
            <span className="font-semibold text-gray-700">{civ.status}</span> · charter v{civ.active_charter_version ?? '—'} ·{' '}
            {civ.protected_invariants} protected invariants
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={runTick} disabled={busy}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50">
            Run coordinator tick
          </button>
          <button onClick={engageKillSwitch} disabled={busy}
            className="rounded-md border border-red-300 bg-red-50 px-3 py-1.5 text-sm text-red-700 hover:bg-red-100 disabled:opacity-50">
            Engage kill switch
          </button>
        </div>
      </div>

      {error && <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {civ.active_emergencies > 0 && (
        <div className="mb-4 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          ⚠ {civ.active_emergencies} active emergency power(s). Protected work may be halted.
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <StatTile label="Societies" value={status.societies_active ?? 0} />
        <StatTile label="Institutions" value={status.institutions_active ?? 0} />
        <StatTile label="Citizens" value={status.citizens_executable ?? 0} />
        <StatTile label="Coalitions" value={status.coalitions_active ?? 0} />
        <StatTile label="Missions executing" value={status.missions_executing ?? 0} />
        <StatTile label="Missions done" value={status.missions_completed ?? 0} />
        <StatTile label="Disputes open" value={status.disputes_open ?? 0} />
        <StatTile label="Learning open" value={status.learning_candidates_open ?? 0} />
        <StatTile label="Expansions open" value={status.expansion_proposals_open ?? 0} />
        <StatTile label="Capability grants" value={status.active_capability_grants ?? 0} />
        <StatTile label="Generality domains" value={status.generality_domains ?? 0} />
        <StatTile label="Active emergencies" value={status.active_emergencies ?? 0} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Societies</h2>
          <div className="space-y-2">
            {(overview.topology?.societies ?? []).map((s) => (
              <div key={s.id} className="flex items-center justify-between text-sm">
                <span className="font-medium text-gray-800">{s.name}</span>
                <span className="text-gray-500">{s.status} · {s.citizen_members} citizens · {s.institutions} institutions</span>
              </div>
            ))}
            {(overview.topology?.societies ?? []).length === 0 && <p className="text-sm text-gray-400">No societies yet.</p>}
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Recent coordinator ticks</h2>
          <div className="space-y-1">
            {(overview.recent_ticks ?? []).map((t) => (
              <div key={t.tick_number} className="flex items-center justify-between text-sm">
                <span className="font-mono text-gray-800">#{t.tick_number}</span>
                <span className="text-gray-500">{t.mode} · routed {t.work_routed}</span>
              </div>
            ))}
            {(overview.recent_ticks ?? []).length === 0 && <p className="text-sm text-gray-400">No ticks recorded.</p>}
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Open missions</h2>
          <div className="space-y-1">
            {(overview.open_work?.missions ?? []).map((m) => (
              <div key={m.id} className="flex items-center justify-between text-sm">
                <span className="truncate text-gray-800">{m.title}</span>
                <span className="ml-2 shrink-0 text-gray-500">{m.status}</span>
              </div>
            ))}
            {(overview.open_work?.missions ?? []).length === 0 && <p className="text-sm text-gray-400">No open missions.</p>}
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Recent activity</h2>
          <div className="max-h-64 space-y-1 overflow-y-auto">
            {(overview.recent_events ?? []).map((e, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="font-mono text-gray-700">{e.event_type}</span>
                <span className="text-gray-400">{new Date(e.occurred_at).toLocaleTimeString()}</span>
              </div>
            ))}
            {(overview.recent_events ?? []).length === 0 && <p className="text-sm text-gray-400">No recent activity.</p>}
          </div>
        </section>
      </div>

      <p className="mt-6 text-xs text-gray-400">
        Generated {overview.generated_at} · data is live from governed civilization APIs (no simulated values).
      </p>
    </div>
  );
}
