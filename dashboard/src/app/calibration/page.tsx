"use client";

/**
 * Governor Calibration Dashboard — Phase 5.
 * 7 panels as per spec:
 * 1. Prediction Ledger
 * 2. Trust Scores
 * 3. Firewall Status
 * 4. Surprise Register
 * 5. Decay Status
 * 6. Self-Audit Report
 * 7. Spot-Audit Interface
 *
 * Read-only by default. Governors can: resolve predictions, run decay cycle,
 * mark surprises investigated, submit spot audits.
 * All write actions require confirmation.
 */

import { useState, useEffect } from "react";
import type {
  CalibrationDashboardState, SurpriseEvent, BeliefStatus,
  TrustScore, DecayStatus, SelfAuditReport, SpotAuditRequest
} from "../../types/calibration";
import {
  getDashboardState, getSurprises, getBeliefs, getTrustScores,
  getDecayStatus, getSelfAuditReport, getSpotAuditLog,
  markSurpriseInvestigated, runDecayCycle, submitSpotAudit,
  getLedger, resolvePredicton,
} from "../../lib/calibration-api";

const STATUS_COLORS: Record<string, string> = {
  provisional: "bg-yellow-100 text-yellow-800",
  simulation_supported: "bg-blue-100 text-blue-800",
  reality_validated: "bg-green-100 text-green-800",
  quarantined: "bg-red-100 text-red-800",
  retired: "bg-gray-100 text-gray-700",
};

function Badge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? "bg-gray-100 text-gray-700";
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cls}`}>{status}</span>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <h2 className="text-base font-semibold text-gray-900 mb-3">{title}</h2>
      {children}
    </section>
  );
}

export default function CalibrationDashboard() {
  const [summary, setSummary] = useState<CalibrationDashboardState | null>(null);
  const [surprises, setSurprises] = useState<SurpriseEvent[]>([]);
  const [beliefs, setBeliefs] = useState<BeliefStatus[]>([]);
  const [trustScores, setTrustScores] = useState<TrustScore[]>([]);
  const [decayStatus, setDecayStatus] = useState<DecayStatus[]>([]);
  const [selfAudit, setSelfAudit] = useState<SelfAuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  // Spot audit form state
  const [spotAuditForm, setSpotAuditForm] = useState<Partial<SpotAuditRequest>>({});
  const [spotAuditLog, setSpotAuditLog] = useState<any[]>([]);

  async function loadAll() {
    try {
      const [s, su, b, t, d, sa, sal] = await Promise.all([
        getDashboardState(),
        getSurprises(),
        getBeliefs(),
        getTrustScores(),
        getDecayStatus(),
        getSelfAuditReport(),
        getSpotAuditLog(),
      ]);
      setSummary(s);
      setSurprises(su);
      setBeliefs(b);
      setTrustScores(t);
      setDecayStatus(d);
      setSelfAudit(sa);
      setSpotAuditLog(sal);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  const TABS = [
    "Ledger Summary",
    "Trust Scores",
    "Firewall",
    "Surprises",
    "Decay",
    "Self-Audit",
    "Spot Audit",
  ];

  if (loading) return <div className="p-8 text-gray-500">Loading calibration dashboard…</div>;
  if (error) return <div className="p-8 text-red-600">Error: {error}</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Governor Calibration Dashboard</h1>
        <p className="text-sm text-gray-500 mb-6">
          Live calibration state. Last updated: {summary?.last_updated ?? "—"}
        </p>

        {/* Summary cards */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white border rounded-lg p-4">
              <div className="text-2xl font-bold">{summary.ledger_summary.total}</div>
              <div className="text-sm text-gray-500">Total Predictions</div>
              <div className="text-xs text-gray-400">{summary.ledger_summary.resolved} resolved</div>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <div className={`text-2xl font-bold ${summary.trust_summary.agents_degraded > 0 ? "text-amber-600" : "text-gray-900"}`}>
                {summary.trust_summary.agents_degraded}
              </div>
              <div className="text-sm text-gray-500">Degraded Agents</div>
              <div className="text-xs text-gray-400">trust_factor &lt; 0.5</div>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <div className={`text-2xl font-bold ${summary.surprise_summary.uninvestigated > 0 ? "text-red-600" : "text-gray-900"}`}>
                {summary.surprise_summary.uninvestigated}
              </div>
              <div className="text-sm text-gray-500">Uninvestigated Surprises</div>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <div className="text-2xl font-bold text-green-700">{summary.firewall_summary.reality_validated}</div>
              <div className="text-sm text-gray-500">Reality-Validated Beliefs</div>
              <div className="text-xs text-gray-400">{summary.firewall_summary.provisional} provisional</div>
            </div>
          </div>
        )}

        {/* Tab navigation */}
        <div className="flex gap-1 mb-4 flex-wrap">
          {TABS.map((t, i) => (
            <button
              key={t}
              onClick={() => setActiveTab(i)}
              className={`px-3 py-1.5 text-sm rounded-md font-medium transition-colors ${
                activeTab === i
                  ? "bg-indigo-600 text-white"
                  : "bg-white text-gray-600 border hover:bg-gray-50"
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Panel 1 — Ledger Summary */}
        {activeTab === 0 && (
          <Panel title="Prediction Ledger">
            <div className="text-sm text-gray-600 mb-2">
              {summary?.ledger_summary.post_hoc_flagged} post-hoc flagged (excluded from calibration math)
              &nbsp;·&nbsp; {summary?.ledger_summary.surprises} surprises triggered
            </div>
            <p className="text-xs text-gray-400">
              Pre-registration columns are immutable (DB-enforced). Resolution requires external ground truth.
            </p>
          </Panel>
        )}

        {/* Panel 2 — Trust Scores */}
        {activeTab === 1 && (
          <Panel title="Trust Scores">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b">
                    <th className="pb-2 pr-4">Agent</th>
                    <th className="pb-2 pr-4">Domain</th>
                    <th className="pb-2 pr-4">Horizon</th>
                    <th className="pb-2 pr-4">Trust Factor</th>
                    <th className="pb-2 pr-4">ECE</th>
                    <th className="pb-2 pr-4">N Resolved</th>
                    <th className="pb-2">Forced Down</th>
                  </tr>
                </thead>
                <tbody>
                  {trustScores.map((ts, i) => (
                    <tr key={i} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-mono text-xs">{ts.subject_id}</td>
                      <td className="py-2 pr-4">{ts.domain}</td>
                      <td className="py-2 pr-4">{ts.horizon_class}</td>
                      <td className={`py-2 pr-4 font-medium ${ts.trust_factor < 0.5 ? "text-amber-600" : "text-green-700"}`}>
                        {(ts.trust_factor * 100).toFixed(0)}%
                      </td>
                      <td className={`py-2 pr-4 ${ts.ece && ts.ece > 0.1 ? "text-red-600" : ""}`}>
                        {ts.ece != null ? ts.ece.toFixed(3) : "—"}
                      </td>
                      <td className="py-2 pr-4">{ts.n_resolved}</td>
                      <td className="py-2">{ts.force_downgrade ? "YES" : "—"}</td>
                    </tr>
                  ))}
                  {trustScores.length === 0 && (
                    <tr><td colSpan={7} className="py-4 text-center text-gray-400">No trust scores yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Panel>
        )}

        {/* Panel 3 — Firewall Status */}
        {activeTab === 2 && (
          <Panel title="Reality / Simulation Firewall">
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 mb-3">
              sim_support_count is displayed for transparency but is NOT a promotion gate.
              Only pre-registered, externally-scored predictions can promote to reality_validated.
            </div>
            <div className="space-y-2">
              {beliefs.map(b => (
                <div key={b.belief_id} className="border rounded p-3 text-sm">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge status={b.validation_status} />
                    <span className="text-xs text-gray-400 font-mono">{b.belief_id.slice(0, 8)}</span>
                  </div>
                  <div className="text-gray-800">{b.statement}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Sim support count: {b.sim_support_count} (ignored in promotion gate)
                    {b.validation_status === "reality_validated" && b.promoted_at && (
                      <> · Promoted: {new Date(b.promoted_at).toLocaleDateString()}</>
                    )}
                  </div>
                </div>
              ))}
              {beliefs.length === 0 && <p className="text-gray-400 text-sm">No beliefs registered</p>}
            </div>
          </Panel>
        )}

        {/* Panel 4 — Surprise Register */}
        {activeTab === 3 && (
          <Panel title="Surprise Register">
            <div className="space-y-2">
              {surprises.map(s => (
                <div key={s.surprise_id} className={`border rounded p-3 text-sm ${!s.investigated ? "border-red-200 bg-red-50" : ""}`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-medium ${!s.investigated ? "text-red-700" : "text-gray-500"}`}>
                      {!s.investigated ? "UNINVESTIGATED" : "Investigated"}
                    </span>
                    <span className="text-xs text-gray-400">score: {s.surprise_score.toFixed(3)}</span>
                  </div>
                  <div>Agent: <span className="font-medium">{s.producing_agent_id}</span> · Domain: {s.domain}</div>
                  <div className="text-xs text-gray-600">
                    p={s.stated_probability.toFixed(2)} resolved {String(s.actual_outcome).toUpperCase()}
                  </div>
                  {!s.investigated && (
                    <button
                      onClick={async () => {
                        const notes = window.prompt("Investigation notes:");
                        if (notes) {
                          await markSurpriseInvestigated(s.surprise_id, notes);
                          await loadAll();
                        }
                      }}
                      className="mt-2 text-xs text-red-700 underline"
                    >
                      Mark investigated
                    </button>
                  )}
                </div>
              ))}
              {surprises.length === 0 && <p className="text-gray-400 text-sm">No surprises registered</p>}
            </div>
          </Panel>
        )}

        {/* Panel 5 — Decay Status */}
        {activeTab === 4 && (
          <Panel title="Decay Tracker">
            <button
              onClick={async () => { await runDecayCycle(); await loadAll(); }}
              className="mb-3 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              Run Decay Cycle
            </button>
            <div className="space-y-2">
              {decayStatus.map(d => (
                <div key={d.belief_id} className={`border rounded p-3 text-sm ${d.warning ? "border-amber-300 bg-amber-50" : ""}`}>
                  <div className="flex items-center gap-2">
                    <Badge status={d.validation_status} />
                    {d.warning && <span className="text-xs text-amber-700 font-medium">EXPIRING SOON</span>}
                  </div>
                  <div className="mt-1 text-gray-800">{d.statement}</div>
                  <div className="text-xs text-gray-500 mt-1">
                    Expires in {d.days_until_expiry.toFixed(0)} days · half-life: {d.half_life_days}d · domain: {d.domain}
                  </div>
                </div>
              ))}
              {decayStatus.length === 0 && <p className="text-gray-400 text-sm">No decaying beliefs</p>}
            </div>
          </Panel>
        )}

        {/* Panel 6 — Self-Audit */}
        {activeTab === 5 && selfAudit && (
          <Panel title="Self-Audit Report">
            <div className="text-xs text-gray-500 mb-3">Generated: {new Date(selfAudit.generated_at).toLocaleString()}</div>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div className="bg-gray-50 rounded p-3">
                <div className="text-xl font-bold">{selfAudit.self_prediction_count}</div>
                <div className="text-xs text-gray-500">Self-predictions</div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className="text-xl font-bold">{selfAudit.self_predictions_resolved}</div>
                <div className="text-xs text-gray-500">Resolved</div>
              </div>
              <div className="bg-gray-50 rounded p-3">
                <div className={`text-xl font-bold ${selfAudit.self_ece != null && selfAudit.self_ece > 0.1 ? "text-red-600" : ""}`}>
                  {selfAudit.self_ece != null ? selfAudit.self_ece.toFixed(3) : "—"}
                </div>
                <div className="text-xs text-gray-500">Self-ECE</div>
              </div>
            </div>
            <div className="text-xs bg-yellow-50 border border-yellow-200 rounded p-3 mb-3">
              <strong>Blind Spot Limit:</strong> {selfAudit.stated_blind_spot_limit}
            </div>
            <div className="text-sm">
              Trend: <span className="font-medium">{selfAudit.trust_score_trend}</span>
              &nbsp;·&nbsp; Spot audit ready: <span className="font-medium text-green-700">
                {selfAudit.spot_audit_ready ? "YES (unannounced)" : "NO"}
              </span>
            </div>
          </Panel>
        )}

        {/* Panel 7 — Spot Audit */}
        {activeTab === 6 && (
          <Panel title="Spot-Audit Interface">
            <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 mb-4">
              Spot audits are UNANNOUNCED. The engine cannot anticipate or prepare for them.
              The prediction sample is randomly selected by the system.
            </div>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                if (!spotAuditForm.auditor_id || !spotAuditForm.findings) return;
                await submitSpotAudit({
                  auditor_id: spotAuditForm.auditor_id!,
                  findings: spotAuditForm.findings!,
                  passed: spotAuditForm.passed ?? false,
                  prediction_sample_ids: spotAuditForm.prediction_sample_ids ?? [],
                });
                setSpotAuditForm({});
                await loadAll();
              }}
              className="space-y-3 mb-6"
            >
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Auditor ID</label>
                <input
                  className="w-full border rounded px-3 py-2 text-sm"
                  value={spotAuditForm.auditor_id ?? ""}
                  onChange={e => setSpotAuditForm(f => ({ ...f, auditor_id: e.target.value }))}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Findings</label>
                <textarea
                  className="w-full border rounded px-3 py-2 text-sm"
                  rows={3}
                  value={spotAuditForm.findings ?? ""}
                  onChange={e => setSpotAuditForm(f => ({ ...f, findings: e.target.value }))}
                  required
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="passed"
                  checked={spotAuditForm.passed ?? false}
                  onChange={e => setSpotAuditForm(f => ({ ...f, passed: e.target.checked }))}
                />
                <label htmlFor="passed" className="text-sm">Audit passed</label>
              </div>
              <button type="submit" className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-md hover:bg-indigo-700">
                Submit Spot Audit
              </button>
            </form>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Audit Log</h3>
            <div className="space-y-2">
              {spotAuditLog.map((a: any) => (
                <div key={a.audit_id} className={`border rounded p-3 text-sm ${a.passed ? "border-green-200" : "border-red-200"}`}>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-medium ${a.passed ? "text-green-700" : "text-red-700"}`}>
                      {a.passed ? "PASSED" : "FAILED"}
                    </span>
                    <span className="text-xs text-gray-400">{a.auditor_id} · {new Date(a.conducted_at).toLocaleString()}</span>
                  </div>
                  <div className="text-gray-700 mt-1">{a.findings}</div>
                </div>
              ))}
              {spotAuditLog.length === 0 && <p className="text-gray-400 text-sm">No spot audits on record</p>}
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}
