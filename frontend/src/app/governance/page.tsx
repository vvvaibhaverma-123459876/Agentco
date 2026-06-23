'use client';

import React, { useEffect, useState } from 'react';

interface GovernanceStatus {
  rbac_operational: boolean;
  roles_count: number;
  permissions_count: number;
  timestamp: string;
}

interface AuditEvent {
  id: string;
  actor_entity_id: string;
  action: string;
  resource: string;
  permission_granted: boolean;
  created_at: string;
}

export default function GovernancePage() {
  const [status, setStatus] = useState<GovernanceStatus | null>(null);
  const [recentEvents, setRecentEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGovernanceStatus = async () => {
      try {
        setLoading(true);

        // Fetch governance status
        const statusResponse = await fetch('/api/governance/status', {
          headers: {
            'x-actor-id': 'dashboard',
          },
        });

        if (!statusResponse.ok) {
          throw new Error('Failed to fetch governance status');
        }

        const statusData = await statusResponse.json();
        setStatus(statusData.status);

        // Fetch recent audit events
        const auditResponse = await fetch('/api/governance/audit-trail?limit=10', {
          headers: {
            'x-actor-id': 'dashboard',
          },
        });

        if (auditResponse.ok) {
          const auditData = await auditResponse.json();
          setRecentEvents(auditData.audit_trail || []);
        }

        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchGovernanceStatus();
  }, []);

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-4xl font-bold text-gray-900">Governance Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Civilization Calibration & Trust Governance System
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-semibold">Error</p>
          <p>{error}</p>
        </div>
      )}

      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-600">Loading governance status...</p>
        </div>
      ) : (
        <>
          {/* Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
              <p className="text-gray-600 text-sm font-semibold">RBAC Status</p>
              <p className="text-3xl font-bold text-green-600 mt-2">
                {status?.rbac_operational ? 'Operational' : 'Down'}
              </p>
              <p className="text-gray-500 text-sm mt-2">Access Control System</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-blue-500">
              <p className="text-gray-600 text-sm font-semibold">Roles</p>
              <p className="text-3xl font-bold text-blue-600 mt-2">
                {status?.roles_count || 0}
              </p>
              <p className="text-gray-500 text-sm mt-2">Governance Roles Defined</p>
            </div>

            <div className="bg-white rounded-lg shadow p-6 border-l-4 border-purple-500">
              <p className="text-gray-600 text-sm font-semibold">Permissions</p>
              <p className="text-3xl font-bold text-purple-600 mt-2">
                {status?.permissions_count || 0}
              </p>
              <p className="text-gray-500 text-sm mt-2">Fine-Grained Permissions</p>
            </div>
          </div>

          {/* Seven Non-Negotiable Rules */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b">
              <h2 className="text-xl font-bold text-gray-900">
                Non-Negotiable Governance Rules
              </h2>
            </div>
            <div className="p-6 space-y-3">
              {[
                'No direct calibration mutation',
                'No self-certification',
                'No silent trust changes',
                'No eval-threshold tampering',
                'No simulation-to-reality leakage',
                'No unilateral civilization override',
                'Preserve existing safety invariants',
              ].map((rule, i) => (
                <div key={i} className="flex items-center space-x-3">
                  <span className="text-green-600 font-bold text-lg">✓</span>
                  <span className="text-gray-700">{rule}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Audit Events */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b">
              <h2 className="text-xl font-bold text-gray-900">Recent Governance Events</h2>
            </div>
            {recentEvents.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                        Actor
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                        Action
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                        Resource
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                        Time
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {recentEvents.map((event) => (
                      <tr key={event.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 text-sm text-gray-900 font-mono">
                          {event.actor_entity_id}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-700">{event.action}</td>
                        <td className="px-6 py-4 text-sm text-gray-700">{event.resource}</td>
                        <td className="px-6 py-4 text-sm">
                          <span
                            className={`px-2 py-1 rounded text-xs font-semibold ${
                              event.permission_granted
                                ? 'bg-green-100 text-green-800'
                                : 'bg-red-100 text-red-800'
                            }`}
                          >
                            {event.permission_granted ? 'Allowed' : 'Denied'}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {new Date(event.created_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="p-6 text-center text-gray-600">
                No recent events
              </div>
            )}
          </div>

          {/* System Information */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-blue-50 rounded-lg p-6 border border-blue-200">
              <h3 className="font-bold text-blue-900 mb-3">RBAC Architecture</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>✓ 5 governance roles (viewer → admin)</li>
                <li>✓ 10 fine-grained permissions</li>
                <li>✓ Database-level enforcement</li>
                <li>✓ Immutable audit trail</li>
              </ul>
            </div>

            <div className="bg-green-50 rounded-lg p-6 border border-green-200">
              <h3 className="font-bold text-green-900 mb-3">Governance Gates</h3>
              <ul className="text-sm text-green-800 space-y-1">
                <li>✓ Emergency freeze check</li>
                <li>✓ Protected surface validation</li>
                <li>✓ Trust policy enforcement</li>
                <li>✓ Reputation event recording</li>
              </ul>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
