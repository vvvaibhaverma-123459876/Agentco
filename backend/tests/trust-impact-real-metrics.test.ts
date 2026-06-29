import { db } from '../src/db/client';
import { TrustImpactAssessmentService } from '../src/services/trust-impact-assessment.service';

describe('TrustImpactAssessmentService real metric calculations', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('compares candidate metrics against baseline metrics without default-perfect output', async () => {
    const service = new TrustImpactAssessmentService();
    const query = jest.spyOn(db, 'query') as unknown as jest.Mock;
    query
      .mockResolvedValueOnce({
        rows: [
          { metric_name: 'calibration_error', metric_value: 0.04 },
          { metric_name: 'average_confidence', metric_value: 0.60 },
          { metric_name: 'false_positive_rate', metric_value: 0.10 },
          { metric_name: 'false_negative_rate', metric_value: 0.12 },
        ],
      } as any)
      .mockResolvedValueOnce({
        rows: [
          { metric_name: 'calibration_error', metric_value: 0.07 },
          { metric_name: 'average_confidence', metric_value: 0.66 },
          { metric_name: 'false_positive_rate', metric_value: 0.14 },
          { metric_name: 'false_negative_rate', metric_value: 0.10 },
          { metric_name: 'safety_threshold_compliance', metric_value: 0.96 },
          { metric_name: 'rollback_feasibility', metric_value: 0.82 },
          { metric_name: 'audit_completeness', metric_value: 0.70 },
        ],
      } as any)
      .mockResolvedValueOnce({ rows: [] } as any)
      .mockResolvedValueOnce({ rows: [{ weighted_impact: -0.2 }] } as any)
      .mockResolvedValueOnce({ rows: [{ open_count: '1', total_count: '2' }] } as any)
      .mockResolvedValueOnce({ rows: [{ simulation_count: '1', total_count: '4' }] } as any);

    const metrics = await service.compareAgainstBaseline(
      '00000000-0000-4000-8000-000000000001',
      '00000000-0000-4000-8000-000000000002'
    );

    expect(query).toHaveBeenCalled();
    expect(metrics.calibration_regression).toBeCloseTo(0.03);
    expect(metrics.confidence_shift).toBeCloseTo(0.06);
    expect(metrics.false_positive_impact).toBeCloseTo(0.04);
    expect(metrics.false_negative_impact).toBeCloseTo(-0.02);
    expect(metrics.reputation_impact).toBeCloseTo(-0.2);
    expect(metrics.dispute_impact).toBeCloseTo(0.5);
    expect(metrics.simulation_leakage_risk).toBeCloseTo(0.25);
    expect(metrics.audit_completeness).toBeLessThan(1);
  });

  it('derives reputation, dispute, and simulation risk from ledgers', async () => {
    const service = new TrustImpactAssessmentService();
    const query = jest.spyOn(db, 'query') as unknown as jest.Mock;
    query
      .mockResolvedValueOnce({ rows: [{ weighted_impact: 0.35 }] } as any)
      .mockResolvedValueOnce({ rows: [{ open_count: '2', total_count: '5' }] } as any)
      .mockResolvedValueOnce({ rows: [{ simulation_count: '3', total_count: '6' }] } as any);

    await expect(service.assessReputationImpact('00000000-0000-4000-8000-000000000001')).resolves.toBeCloseTo(0.35);
    await expect(service.assessDisputeImpact('00000000-0000-4000-8000-000000000001')).resolves.toBeCloseTo(0.4);
    await expect(service.assessSimulationLeakageRisk('00000000-0000-4000-8000-000000000001')).resolves.toBeCloseTo(0.5);
  });
});
