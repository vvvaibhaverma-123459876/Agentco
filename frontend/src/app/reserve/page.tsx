'use client';

import { useEffect, useState } from 'react';

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:3001';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

interface Credential {
  agent_id: string;
  domain: string;
  horizon_class: string;
  trust_factor: number;
  n_resolved: number;
  computed_at: string;
}

interface OracleStanding {
  subject_id: string;
  trust_factor: number;
  n_resolved: number;
}

interface VerifyResult {
  stored: number;
  recomputed: number;
  match: boolean;
}

interface VerifyModal {
  agentId: string;
  loading: boolean;
  result: VerifyResult | null;
  error: string | null;
}

export default function ReservePage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [oracleStandings, setOracleStandings] = useState<OracleStanding[]>([]);
  const [credsError, setCredsError] = useState<string | null>(null);
  const [oracleError, setOracleError] = useState<string | null>(null);
  const [modal, setModal] = useState<VerifyModal | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await apiFetch<{ credentials: Credential[] }>('/api/reserve/credentials');
        setCredentials(data.credentials ?? []);
      } catch {
        setCredsError('Could not load credentials — is the backend running?');
      }
    })();
    (async () => {
      try {
        const data = await apiFetch<{ standings: OracleStanding[] }>(
          '/api/reserve/oracle-standing'
        );
        setOracleStandings(data.standings ?? []);
      } catch {
        setOracleError('Could not load oracle standing — is the backend running?');
      }
    })();
  }, []);

  async function handleVerify(agentId: string) {
    setModal({ agentId, loading: true, result: null, error: null });
    try {
      const data = await apiFetch<VerifyResult>(`/api/reserve/verify/${agentId}`, {
        method: 'POST',
      });
      setModal({ agentId, loading: false, result: data, error: null });
    } catch (err: unknown) {
      setModal({
        agentId,
        loading: false,
        result: null,
        error: err instanceof Error ? err.message : 'Verification failed.',
      });
    }
  }

  const empty =
    !credsError && credentials.length === 0;

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">Epistemic Reserve</h1>
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-indigo-800">
          These credentials are signed but not secret. Anyone can recompute them from the public
          ledger.
        </p>
      </div>

      {/* Credentials */}
      <h2 className="text-base font-semibold text-gray-800 mb-3">Agent Credentials</h2>

      {credsError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-6">
          {credsError}
        </div>
      )}

      {empty && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6 text-center">
          <p className="text-gray-500 text-sm">
            No credentials computed yet. Run the calibration pipeline with real predictions to
            generate credentials.
          </p>
        </div>
      )}

      {credentials.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {credentials.map((cred, i) => (
            <div key={i} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex items-start justify-between mb-2">
                <div>
                  <p className="font-semibold text-gray-800">{cred.agent_id}</p>
                  <p className="text-xs text-gray-500">
                    {cred.domain} · {cred.horizon_class}
                  </p>
                </div>
                <span
                  className={`text-xl font-bold ${
                    cred.trust_factor >= 0.8
                      ? 'text-green-600'
                      : cred.trust_factor >= 0.6
                      ? 'text-yellow-600'
                      : 'text-red-600'
                  }`}
                >
                  {(cred.trust_factor * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex gap-6 text-sm text-gray-500 mb-3">
                <span>Resolved: {cred.n_resolved}</span>
                <span>Computed: {new Date(cred.computed_at).toLocaleDateString()}</span>
              </div>
              <button
                onClick={() => handleVerify(cred.agent_id)}
                className="border border-indigo-300 text-indigo-700 px-3 py-1.5 rounded text-xs font-medium hover:bg-indigo-50 transition-colors"
              >
                Verify this credential
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Oracle Standing */}
      <h2 className="text-base font-semibold text-gray-800 mb-3">Oracle Standing</h2>

      {oracleError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 mb-4">
          {oracleError}
        </div>
      )}

      {!oracleError && oracleStandings.length === 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 text-center">
          <p className="text-gray-500 text-sm">
            No credentials computed yet. Run the calibration pipeline with real predictions to
            generate credentials.
          </p>
        </div>
      )}

      {oracleStandings.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 font-medium">Subject</th>
                <th className="px-4 py-2 font-medium">Trust Factor</th>
                <th className="px-4 py-2 font-medium">Resolved</th>
              </tr>
            </thead>
            <tbody>
              {oracleStandings.map((s, i) => (
                <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-700 font-mono text-xs">{s.subject_id}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`font-semibold ${
                        s.trust_factor >= 0.8
                          ? 'text-green-600'
                          : s.trust_factor >= 0.6
                          ? 'text-yellow-600'
                          : 'text-red-600'
                      }`}
                    >
                      {(s.trust_factor * 100).toFixed(1)}%
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-600">{s.n_resolved}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Verify Modal */}
      {modal && (
        <div
          className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
          onClick={() => setModal(null)}
        >
          <div
            className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-base font-semibold text-gray-900 mb-3">
              Credential Verification — {modal.agentId}
            </h3>

            {modal.loading && <p className="text-gray-500 text-sm">Verifying…</p>}

            {modal.error && (
              <p className="text-red-600 text-sm">{modal.error}</p>
            )}

            {modal.result && (
              <div>
                <div className="space-y-2 mb-4 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Stored:</span>
                    <span className="font-mono">{modal.result.stored.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Recomputed:</span>
                    <span className="font-mono">{modal.result.recomputed.toFixed(4)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Match:</span>
                    <span
                      className={`font-bold ${
                        modal.result.match ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {modal.result.match ? '✓ VERIFIED' : '✗ MISMATCH'}
                    </span>
                  </div>
                </div>
                <div
                  className={`rounded p-3 text-sm font-medium text-center ${
                    modal.result.match
                      ? 'bg-green-50 text-green-700'
                      : 'bg-red-50 text-red-700'
                  }`}
                >
                  {modal.result.match
                    ? 'Credential is authentic and untampered.'
                    : 'Warning: credential does not match ledger data.'}
                </div>
              </div>
            )}

            <button
              onClick={() => setModal(null)}
              className="mt-4 w-full border border-gray-300 text-gray-700 py-2 rounded text-sm hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
