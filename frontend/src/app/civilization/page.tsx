'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

interface Institution {
  institution_id: string;
  institution_name: string;
  mission: string;
  departments: string[];
}

interface Review {
  review_id: string;
  reviewed_output_id: string;
  status: string;
  reviewer_institution: string;
  reviewed_institution: string;
  created_at: string;
}

interface Reputation {
  institution_name: string;
  score: number;
  last_updated: string;
}

interface GovernanceDecision {
  decision_id: string;
  decision_type: string;
  status: string;
  proposed_by: string;
  created_at: string;
}

const STATUS_BADGE: Record<string, string> = {
  proposed: 'bg-blue-100 text-blue-700',
  under_review: 'bg-yellow-100 text-yellow-700',
  approved: 'bg-green-100 text-green-700',
  rejected: 'bg-red-100 text-red-700',
  challenged: 'bg-orange-100 text-orange-700',
};

async function fetchJson(url: string) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
}

export default function CivilizationPage() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [reputation, setReputation] = useState<Reputation[]>([]);
  const [governance, setGovernance] = useState<GovernanceDecision[]>([]);
  const [notInitialized, setNotInitialized] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchJson(`${API}/api/civilization/institutions`),
      fetchJson(`${API}/api/civilization/reviews`),
      fetchJson(`${API}/api/civilization/reputation`),
      fetchJson(`${API}/api/civilization/governance`),
    ])
      .then(([inst, rev, rep, gov]) => {
        setInstitutions(inst.institutions || inst || []);
        setReviews(rev.reviews || rev || []);
        setReputation(rep.reputation || rep || []);
        setGovernance(gov.decisions || gov || []);
      })
      .catch(() => setNotInitialized(true))
      .finally(() => setLoading(false));
  }, []);

  if (notInitialized) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Civilization — Multi-Institution Governance</h1>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-yellow-800">
          <div className="font-semibold mb-2">Civilization layer not yet initialized.</div>
          <div className="text-sm">Run the seed script:</div>
          <pre className="mt-2 bg-yellow-100 rounded p-3 text-xs font-mono">python3 reserve/tools/seed_civilization.py</pre>
        </div>
      </div>
    );
  }

  // Self-cert ban check: any review where reviewer === reviewed institution?
  const selfCertViolation = reviews.find(r => r.reviewer_institution === r.reviewed_institution);

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Civilization — Multi-Institution Governance</h1>
        <p className="text-gray-500 mt-1">Cross-institutional review and reputation system</p>
      </div>

      {/* Self-cert ban indicator */}
      {selfCertViolation ? (
        <div className="bg-red-50 border border-red-300 rounded-lg p-4 mb-6 text-red-800 font-medium">
          ⚠ Self-certification violation detected — {selfCertViolation.reviewer_institution} approved its own output (review {selfCertViolation.review_id.slice(0, 8)}).
        </div>
      ) : (
        <div className="bg-green-50 border border-green-300 rounded-lg p-4 mb-6 text-green-800 font-medium">
          ✓ Self-certification ban active — no institution has approved its own output.
        </div>
      )}

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading civilization data...</div>
      ) : (
        <div className="space-y-6">
          {/* Institution cards */}
          <div>
            <h2 className="font-semibold text-gray-800 mb-3">Institutions ({institutions.length})</h2>
            <div className="grid grid-cols-2 gap-4">
              {institutions.map(inst => (
                <div key={inst.institution_id} className="bg-white rounded-lg border border-gray-200 p-4">
                  <div className="font-medium text-gray-900">{inst.institution_name}</div>
                  <div className="text-xs text-gray-500 mt-1 mb-3">{inst.mission}</div>
                  {inst.departments && inst.departments.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {inst.departments.map(d => (
                        <span key={d} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">{d}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Active reviews */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Active Reviews ({reviews.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Review ID', 'Output ID', 'Status', 'Reviewer', 'Reviewed', 'Created'].map(h => (
                      <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {reviews.length === 0 ? (
                    <tr><td colSpan={6} className="text-center py-6 text-gray-400">No reviews found.</td></tr>
                  ) : reviews.map(r => (
                    <tr key={r.review_id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{r.review_id.slice(0, 8)}</td>
                      <td className="px-4 py-2 font-mono text-xs">{r.reviewed_output_id?.slice(0, 8)}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[r.status] || 'bg-gray-100 text-gray-600'}`}>
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{r.reviewer_institution}</td>
                      <td className="px-4 py-2 text-gray-600">{r.reviewed_institution}</td>
                      <td className="px-4 py-2 text-xs text-gray-400">{new Date(r.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Reputation scores */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Reputation Scores</h2>
            </div>
            <div className="divide-y divide-gray-50">
              {reputation.length === 0 ? (
                <div className="px-4 py-6 text-gray-400 text-sm">No reputation data.</div>
              ) : reputation.map((rep, i) => (
                <div key={i} className="px-4 py-3 flex items-center justify-between">
                  <div className="font-medium text-gray-900">{rep.institution_name}</div>
                  <div className="flex items-center gap-4">
                    <div className="w-32 bg-gray-100 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${Math.min(100, rep.score)}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold text-gray-700 w-12 text-right">{rep.score.toFixed(1)}</span>
                    <span className="text-xs text-gray-400">{new Date(rep.last_updated).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Governance decisions */}
          <div className="bg-white rounded-lg border border-gray-200">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-800">Governance Decisions ({governance.length})</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    {['Decision ID', 'Type', 'Status', 'Proposed By', 'Created'].map(h => (
                      <th key={h} className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {governance.length === 0 ? (
                    <tr><td colSpan={5} className="text-center py-6 text-gray-400">No governance decisions.</td></tr>
                  ) : governance.map(d => (
                    <tr key={d.decision_id} className="hover:bg-gray-50">
                      <td className="px-4 py-2 font-mono text-xs">{d.decision_id.slice(0, 8)}</td>
                      <td className="px-4 py-2 text-gray-600">{d.decision_type}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[d.status] || 'bg-gray-100 text-gray-600'}`}>
                          {d.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-600">{d.proposed_by}</td>
                      <td className="px-4 py-2 text-xs text-gray-400">{new Date(d.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
