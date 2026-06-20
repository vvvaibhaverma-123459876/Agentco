import { CivilizationPageShell, Pill, Section, StatGrid } from '@/components/civilization/CivilizationPageShell';
import { civilizationApi } from '@/lib/civilization-api';

export default async function ReviewDashboardPage() {
  const reviews = await civilizationApi.getReviews();
  const pending = reviews.filter((review) => review.finalDecision === 'pending').length;

  return (
    <CivilizationPageShell
      eyebrow="Review Dashboard"
      title="Independent Review Queue"
      description="Tracks proposed outputs, reviewer institutions, challenge status, evidence, final decisions, and linked calibration claims."
    >
      <StatGrid
        stats={[
          { label: 'Reviews', value: reviews.length },
          { label: 'Pending decisions', value: pending, tone: pending ? 'warn' : 'good' },
          { label: 'Linked claims', value: reviews.reduce((sum, review) => sum + review.linkedCalibrationClaims.length, 0) },
          { label: 'Mock/offline mode', value: 'enabled' },
        ]}
      />

      <Section title="Output Reviews" label="Shipped">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100 text-sm">
            <thead className="text-left text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="py-2 pr-4">Output</th>
                <th className="py-2 pr-4">Reviewer</th>
                <th className="py-2 pr-4">Challenge</th>
                <th className="py-2 pr-4">Evidence</th>
                <th className="py-2 pr-4">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {reviews.map((review) => (
                <tr key={review.id}>
                  <td className="py-3 pr-4">
                    <div className="font-medium text-gray-900">{review.output}</div>
                    <div className="text-xs text-gray-500">{review.proposingInstitution}</div>
                  </td>
                  <td className="py-3 pr-4 text-gray-700">{review.reviewerInstitution}</td>
                  <td className="py-3 pr-4"><Pill tone={review.challengeStatus === 'open' ? 'warn' : 'good'}>{review.challengeStatus}</Pill></td>
                  <td className="py-3 pr-4">
                    <div className="flex flex-wrap gap-1.5">
                      {review.evidence.map((item) => <Pill key={item}>{item}</Pill>)}
                    </div>
                  </td>
                  <td className="py-3 pr-4 text-gray-700">{review.finalDecision}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </CivilizationPageShell>
  );
}
