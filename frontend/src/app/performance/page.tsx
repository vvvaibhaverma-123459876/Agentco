'use client';

import { useEffect, useMemo, useState } from 'react';
import { api } from '@/lib/api';
import type { AuditEntry } from '@/types';

type ValidationReport = {
  benchmark: string;
  evidence_quality: string;
  score: number;
  threshold: number;
  status: string;
};

type PerformanceSnapshot = {
  auditEntries: AuditEntry[];
  auditIntegrity: { valid: boolean; broken_at?: string } | null;
  validationReports: ValidationReport[];
  releasePasses: boolean | null;
};

function formatPercent(value: number | null): string {
  return value === null ? 'unverified' : `${(value * 100).toFixed(1)}%`;
}

function latestTimestamp(entries: AuditEntry[]): string {
  const timestamps = entries
    .map(entry => Date.parse(entry.timestamp))
    .filter(value => Number.isFinite(value));
  if (!timestamps.length) return 'no audit entries';
  return new Date(Math.max(...timestamps)).toLocaleString();
}

export default function PerformancePage() {
  const [snapshot, setSnapshot] = useState<PerformanceSnapshot>({
    auditEntries: [],
    auditIntegrity: null,
    validationReports: [],
    releasePasses: null,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      api.audit.list({ limit: 200 }),
      api.audit.verifyIntegrity(),
      api.validation.reports(),
    ])
      .then(([auditResult, integrityResult, validationResult]) => {
        if (cancelled) return;
        setSnapshot({
          auditEntries: auditResult.entries,
          auditIntegrity: integrityResult,
          validationReports: validationResult.reports,
          releasePasses: validationResult.release_passes,
        });
      })
      .catch(err => {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const metrics = useMemo(() => {
    const entries = snapshot.auditEntries;
    const errorEntries = entries.filter(entry => {
      const text = `${entry.action_type} ${entry.input_summary} ${entry.output_summary}`.toLowerCase();
      return text.includes('error') || text.includes('failed') || text.includes('failure') || text.includes('incident');
    });
    const approved = entries.filter(entry => entry.human_approved);
    const confidenceValues = entries
      .map(entry => Number(entry.confidence_score))
      .filter(value => Number.isFinite(value));
    const averageConfidence = confidenceValues.length
      ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
      : null;
    const scoredReports = snapshot.validationReports.filter(report => Number.isFinite(Number(report.score)));
    const averageValidationScore = scoredReports.length
      ? scoredReports.reduce((sum, report) => sum + Number(report.score), 0) / scoredReports.length
      : null;

    return [
      {
        label: 'Audit Events Sampled',
        value: String(entries.length),
        detail: `latest: ${latestTimestamp(entries)}`,
      },
      {
        label: 'Audit Chain',
        value: snapshot.auditIntegrity === null ? 'unverified' : snapshot.auditIntegrity.valid ? 'valid' : 'broken',
        detail: snapshot.auditIntegrity?.broken_at ? `broken at ${snapshot.auditIntegrity.broken_at}` : 'queried from /api/audit/integrity',
      },
      {
        label: 'Observed Error Signals',
        value: String(errorEntries.length),
        detail: 'derived from audit action/input/output text',
      },
      {
        label: 'Human Approved Decisions',
        value: String(approved.length),
        detail: 'from audit log records',
      },
      {
        label: 'Average Logged Confidence',
        value: formatPercent(averageConfidence),
        detail: confidenceValues.length ? `${confidenceValues.length} entries with confidence` : 'no confidence evidence',
      },
      {
        label: 'Validation Score Mean',
        value: averageValidationScore === null ? 'unverified' : averageValidationScore.toFixed(3),
        detail: `${scoredReports.length} validation reports; release gate ${snapshot.releasePasses === null ? 'unverified' : snapshot.releasePasses ? 'pass' : 'fail'}`,
      },
    ];
  }, [snapshot]);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Performance Dashboard</h1>
      <p className="text-gray-500 mt-1">Evidence-derived operational signals from audit and validation APIs.</p>

      {error ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Unable to load performance evidence: {error}
        </div>
      ) : null}

      <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {metrics.map(({ label, value, detail }) => (
          <div key={label} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="text-sm text-gray-500">{label}</div>
            <div className={`mt-1 text-2xl font-bold ${loading ? 'text-gray-400' : 'text-gray-900'}`}>
              {loading ? 'loading...' : value}
            </div>
            <div className="mt-1 text-xs text-gray-400">{loading ? 'waiting for API evidence' : detail}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-gray-700">Evidence Boundary</h2>
        <p className="mt-2 text-sm text-gray-500">
          This page does not infer latency, cost, accuracy, or incident posture without backend evidence.
          Missing records are shown as unverified rather than as passing thresholds.
        </p>
      </div>
    </div>
  );
}
