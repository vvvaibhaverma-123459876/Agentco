'use client';

import { useEffect, useState } from 'react';
import { api } from '@/lib/api';

type Report = {
  benchmark: string;
  evidence_quality: string;
  score: number;
  threshold: number;
  status: string;
};

export default function ValidationPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [releasePasses, setReleasePasses] = useState(false);

  useEffect(() => {
    api.validation.reports()
      .then((data: { release_passes: boolean; reports: Report[] }) => {
        setReleasePasses(data.release_passes);
        setReports(data.reports);
      })
      .catch(console.error);
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Validation Console</h1>
      <p className="text-gray-500 mt-1">Reports distinguish EXTERNAL-VALIDATED and FIXTURE evidence.</p>
      <div className={`mt-4 inline-block rounded px-3 py-1 text-sm font-medium ${releasePasses ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
        release gate: {releasePasses ? 'pass' : 'fail'}
      </div>
      <div className="mt-6 bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>{['Benchmark', 'Evidence', 'Score', 'Threshold', 'Status'].map(h => <th key={h} className="text-left px-4 py-2">{h}</th>)}</tr>
          </thead>
          <tbody>
            {reports.map(report => (
              <tr key={report.benchmark} className="border-t">
                <td className="px-4 py-2">{report.benchmark}</td>
                <td className="px-4 py-2">{report.evidence_quality}</td>
                <td className="px-4 py-2">{report.score}</td>
                <td className="px-4 py-2">{report.threshold}</td>
                <td className="px-4 py-2">{report.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
